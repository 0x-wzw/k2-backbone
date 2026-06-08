import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";
import { execSync } from "child_process";

const DEFAULT_K2_PATH = "/home/ubuntu/.openclaw/workspace/k2-backbone";

export default defineToolPlugin({
  id: "k2-backbone",
  name: "K2-Backbone",
  description: "Kimi K2.6 Production Backbone — decompose, route, execute, compress",
  tools: (tool) => [
    tool({
      name: "k2_decompose",
      description:
        "Decompose a complex task into structured subtasks using K2.6. Returns a JSON TaskSpec.",
      parameters: Type.Object({
        task: Type.String({ description: "The complex task to decompose" }),
        k2Path: Type.Optional(
          Type.String({ description: "Path to k2-backbone repo" }),
        ),
      }),
      execute: async ({ task, k2Path }) => {
        const path = k2Path || DEFAULT_K2_PATH;
        try {
          // Escape task string for Python single-quoted triple-quote
          const escaped = task.replace(/'/g, "'\\''");
          const result = execSync(
            `cd "${path}" && python3 -c "
import sys
sys.path.insert(0, 'src')
from k2_backbone.decomposer.k2_decomposer import K2Decomposer
d = K2Decomposer()
spec = d.decompose('''${escaped}''')
print(spec)
"`,
            { timeout: 60000, encoding: "utf-8" },
          );
          return { output: result.trim() };
        } catch (err) {
          return {
            output: `Error: ${err instanceof Error ? err.message : String(err)}`,
          };
        }
      },
    }),
    tool({
      name: "k2_execute",
      description:
        "Execute a TaskSpec JSON through the K2 pipeline (route + execute + compress).",
      parameters: Type.Object({
        spec_path: Type.String({
          description: "Path to the TaskSpec JSON file",
        }),
        k2Path: Type.Optional(
          Type.String({ description: "Path to k2-backbone repo" }),
        ),
      }),
      execute: async ({ spec_path, k2Path }) => {
        const path = k2Path || DEFAULT_K2_PATH;
        try {
          const result = execSync(
            `cd "${path}" && python3 -m k2_backbone.core.cli_v2 --spec "${spec_path}"`,
            { timeout: 120000, encoding: "utf-8" },
          );
          return { output: result.trim() };
        } catch (err) {
          return {
            output: `Error: ${err instanceof Error ? err.message : String(err)}`,
          };
        }
      },
    }),
    tool({
      name: "k2_compress",
      description:
        "Compress conversation history using Obliviarch compression levels.",
      parameters: Type.Object({
        input_path: Type.String({
          description: "Path to the text file to compress",
        }),
        level: Type.Optional(
          Type.Union(
            [
              Type.Literal("20x"),
              Type.Literal("100x"),
              Type.Literal("500x"),
            ],
            { description: "Compression ratio: 20x, 100x, or 500x" },
          ),
        ),
        k2Path: Type.Optional(
          Type.String({ description: "Path to k2-backbone repo" }),
        ),
      }),
      execute: async ({ input_path, level, k2Path }) => {
        const path = k2Path || DEFAULT_K2_PATH;
        const compressionLevel = level || "20x";
        try {
          const result = execSync(
            `cd "${path}" && python3 -c "
import sys
sys.path.insert(0, 'src')
from k2_backbone.compressor.obliviarch_adapter import ObliviarchAdapter
oa = ObliviarchAdapter()
with open('${input_path}', 'r') as f:
    text = f.read()
result = oa.compress(text, '${compressionLevel}')
print(result)
"`,
            { timeout: 120000, encoding: "utf-8" },
          );
          return { output: result.trim() };
        } catch (err) {
          return {
            output: `Error: ${err instanceof Error ? err.message : String(err)}`,
          };
        }
      },
    }),
    tool({
      name: "k2_route",
      description:
        "Route subtasks to optimal LLM providers using the 10-D Council.",
      parameters: Type.Object({
        spec_path: Type.String({
          description: "Path to the TaskSpec JSON file",
        }),
        mode: Type.Optional(
          Type.String({
            description:
              "Routing mode: borda, cost_first, or quality_first",
          }),
        ),
        k2Path: Type.Optional(
          Type.String({ description: "Path to k2-backbone repo" }),
        ),
      }),
      execute: async ({ spec_path, mode, k2Path }) => {
        const path = k2Path || DEFAULT_K2_PATH;
        const routerMode = mode || "borda";
        try {
          const result = execSync(
            `cd "${path}" && python3 -c "
import sys
sys.path.insert(0, 'src')
import json
from k2_backbone.router.necroswarm_router import NecroSwarmRouter, VoteMethod
cr = NecroSwarmRouter(vote_method=VoteMethod('${routerMode}'))
with open('${spec_path}') as f:
    spec = json.load(f)
plan = cr.route(spec)
print(json.dumps(plan, indent=2))
"`,
            { timeout: 120000, encoding: "utf-8" },
          );
          return { output: result.trim() };
        } catch (err) {
          return {
            output: `Error: ${err instanceof Error ? err.message : String(err)}`,
          };
        }
      },
    }),
  ],
});