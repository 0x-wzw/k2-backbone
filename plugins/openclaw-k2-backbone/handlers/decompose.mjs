// K2 Decompose tool handler
// Calls k2-backbone's decomposer via CLI
import { execSync } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const pluginDir = join(__dirname, '..');

export default async function handler(args, context) {
  const { task } = args;
  const k2Path = context.config?.k2Path || '/home/ubuntu/.openclaw/workspace/k2-backbone';
  
  try {
    const result = execSync(
      `cd ${k2Path} && python3 -c "
import sys
sys.path.insert(0, 'src')
from k2_backbone.decomposer.k2_decomposer import K2Decomposer
d = K2Decomposer()
spec = d.decompose('''${task.replace(/'/g, "'\\''")}''')
print(spec)
"`,
      { timeout: 60000, encoding: 'utf-8' }
    );
    return { content: [{ type: 'text', text: result.trim() }] };
  } catch (err) {
    return { content: [{ type: 'text', text: `Error: ${err.message}` }], isError: true };
  }
}