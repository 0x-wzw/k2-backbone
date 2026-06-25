from __future__ import annotations
"""
Ollama Cloud Decomposer Adapter

Translates natural language task decomposition into structured TaskSpec
using Ollama Cloud models via the native Ollama client.

Strategy: Prompt-for-Decomposition with format='json' enforcement.
No Moonshot dependency — uses OLLAMA_API_KEY against ollama.com.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from ollama import Client as OllamaClient
except ImportError:
    raise ImportError("ollama>=0.6 required. pip install ollama")


# ── Schema constant: the exact prompt we feed the model ─────────────

TASK_DECOMPOSITION_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 3},
        "objective": {"type": "string", "minLength": 10},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string", "minLength": 3},
                    "description": {"type": "string", "minLength": 10},
                    "type": {
                        "type": "string",
                        "enum": [
                            "research", "code_generation", "code_review",
                            "testing", "documentation", "analysis", "writing",
                            "synthesis", "optimization", "data_processing",
                            "visualization", "integration"
                        ]
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^sub_[0-9]{3}$"}
                    },
                    "estimated_tokens": {"type": "integer", "minimum": 128},
                    "success_criteria": {"type": "string", "minLength": 10}
                },
                "required": ["id", "title", "description", "type", "dependencies", "estimated_tokens", "success_criteria"]
            }
        }
    },
    "required": ["title", "objective", "risk_level", "subtasks"]
}

SYSTEM_PROMPT = """You are an expert task decomposer. Given a complex task, break it into subtasks following these rules:

1. Each subtask must be independently executable
2. Respect dependencies — no circular references
3. Estimate token usage realistically (128 min, 200000 max)
4. Risk level should reflect overall task complexity
5. Maximum 20 subtasks for clarity

Return ONLY valid JSON matching the requested schema. No explanations outside the JSON block."""


# ── Data classes ──────────────────────────────────────────────────────

@dataclass
class Subtask:
    id: str
    title: str
    description: str
    type: str
    dependencies: list[str] = field(default_factory=list)
    estimated_tokens: int = 4096
    success_criteria: str = ""
    assigned_model: Optional[str] = None
    budget_allocation: float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> Subtask:
        return cls(
            id=d["id"],
            title=d["title"],
            description=d.get("description", d.get("objective", d["title"])),
            type=d["type"],
            dependencies=d.get("dependencies", []),
            estimated_tokens=d.get("estimated_tokens", 4096),
            success_criteria=d.get("success_criteria", ""),
        )


@dataclass
class TaskSpec:
    task_id: str
    title: str
    description: str
    objective: str
    acceptance_criteria: list[str]
    risk_level: str
    budget: dict
    subtasks: list[Subtask]
    decomposition: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "objective": self.objective,
            "acceptance_criteria": self.acceptance_criteria,
            "risk_level": self.risk_level,
            "budget": self.budget,
            "subtasks": [
                {
                    "id": s.id,
                    "title": s.title,
                    "description": s.description,
                    "type": s.type,
                    "dependencies": s.dependencies,
                    "estimated_tokens": s.estimated_tokens,
                    "success_criteria": s.success_criteria,
                    "assigned_model": s.assigned_model,
                    "budget_allocation": s.budget_allocation,
                }
                for s in self.subtasks
            ],
            "decomposition": self.decomposition,
            "metadata": self.metadata,
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


# ── Core adapter ─────────────────────────────────────────────────────

class K2Decomposer:
    """
    Adapter that prompts an Ollama Cloud model for structured decomposition,
    then maps the result to our TaskSpec schema.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-v4-flash",
        max_subtasks: int = 20,
        budget_usd: float = 10.0,
    ):
        self.client = OllamaClient(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        self.model = model
        self.max_subtasks = max_subtasks
        self.budget_usd = budget_usd

    def decompose(
        self,
        task: str,
        context: str = "",
        options: Optional[dict] = None,
    ) -> TaskSpec:
        """
        Send task to Ollama Cloud, get structured decomposition, map to TaskSpec.
        """
        schema_json = json.dumps(TASK_DECOMPOSITION_SCHEMA, indent=2)
        user_content = f"""Task: {task}

Context: {context or '(none)'}

Maximum subtasks: {self.max_subtasks}

You MUST return a JSON object matching this exact schema:
{schema_json}

Return ONLY the JSON object, no markdown, no code fences, no explanation."""

        # ── Stage 1: Decomposition ─────────────────────────────────
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            format="json",
            stream=False,
            options={"temperature": 0.2},
        )

        raw_content = response["message"]["content"]

        # Strip markdown code fences if the model wraps the JSON
        raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content.strip())
        raw_content = re.sub(r"\s*```$", "", raw_content.strip())

        parsed = json.loads(raw_content)

        # ── Stage 2: Validation ────────────────────────────────────
        self._validate(parsed)

        # ── Stage 3: Map to TaskSpec ──────────────────────────────
        return self._to_task_spec(parsed, task)

    def _validate(self, parsed: dict) -> None:
        """Basic sanity checks before mapping."""
        assert "title" in parsed, "Missing title"
        assert "subtasks" in parsed, "Missing subtasks"
        assert len(parsed["subtasks"]) <= self.max_subtasks, f"Too many subtasks: {len(parsed['subtasks'])}"

        # Check for dependency cycles
        ids = {s["id"] for s in parsed["subtasks"]}
        for s in parsed["subtasks"]:
            for dep in s.get("dependencies", []):
                assert dep in ids, f"Dependency {dep} not found in subtask list"

        # Check for self-reference
        for s in parsed["subtasks"]:
            assert s["id"] not in s.get("dependencies", []), f"Self-dependency: {s['id']}"

    def _to_task_spec(self, parsed: dict, original_task: str) -> TaskSpec:
        """Map decomposition to our TaskSpec schema."""
        subtasks = [Subtask.from_dict(s) for s in parsed["subtasks"]]
        total_tokens = sum(s.estimated_tokens for s in subtasks)

        # Allocate budget proportionally
        for s in subtasks:
            s.budget_allocation = round(s.estimated_tokens / total_tokens, 4)

        return TaskSpec(
            task_id=f"k2_{int(datetime.now().timestamp() * 1000)}",
            title=parsed["title"],
            description=original_task,
            objective=parsed["objective"],
            acceptance_criteria=[s.success_criteria for s in subtasks],
            risk_level=parsed.get("risk_level", "medium"),
            budget={
                "max_usd": self.budget_usd,
                "max_input_tokens": int(total_tokens * 0.6),
                "max_output_tokens": int(total_tokens * 0.4),
                "currency": "USD",
                "priority": "balanced",
            },
            subtasks=subtasks,
            decomposition={
                "model": self.model,
                "estimated_subagents": len(subtasks),
                "decomposition_strategy": "heterogeneous",
                "timestamp": datetime.now().isoformat(),
            },
            metadata={
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "source": "ollama_cloud_decomposer",
            },
        )

    def synthesize(self, results: list[dict], original_task: str) -> str:
        """
        Stage 3: Feed subtask results back to the model for final synthesis.
        Optional — only needed if coherent final output is required.
        """
        synthesis_prompt = f"""Synthesize these subtask outputs into a cohesive deliverable.

Original task: {original_task}

Subtask results:
{json.dumps(results, indent=2, ensure_ascii=False)}

Produce a unified, well-structured response."""

        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a synthesis expert. Combine multiple work products into one coherent deliverable."},
                {"role": "user", "content": synthesis_prompt},
            ],
            stream=False,
            options={"temperature": 0.3},
        )
        return response["message"]["content"]


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Ollama Cloud Decomposer")
    parser.add_argument("task", help="Task description")
    parser.add_argument("--context", default="", help="Additional context")
    parser.add_argument("--model", default="deepseek-v4-flash", help="Ollama Cloud model")
    parser.add_argument("--max-subtasks", type=int, default=20)
    parser.add_argument("--budget", type=float, default=10.0)
    parser.add_argument("--output", type=Path, default=Path("task_spec.json"))
    parser.add_argument("--synthesize", action="store_true", help="Run synthesis stage")
    args = parser.parse_args()

    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        raise SystemExit("OLLAMA_API_KEY not set")

    decomposer = K2Decomposer(
        api_key=api_key,
        model=args.model,
        max_subtasks=args.max_subtasks,
        budget_usd=args.budget,
    )

    print(f"Decomposing: {args.task[:60]}...")
    print(f"Model: {args.model}")
    spec = decomposer.decompose(args.task, context=args.context)
    spec.save(args.output)
    print(f"TaskSpec saved to {args.output}")
    print(f"  Subtasks: {len(spec.subtasks)}")
    print(f"  Risk: {spec.risk_level}")
    print(f"  Budget: ${spec.budget['max_usd']}")

    if args.synthesize:
        # Mock results for demo
        mock_results = [{"subtask_id": s.id, "status": "completed", "output": f"Result for {s.title}"} for s in spec.subtasks]
        synthesis = decomposer.synthesize(mock_results, args.task)
        print("\n--- Synthesis ---\n")
        print(synthesis[:500])


if __name__ == "__main__":
    main()
