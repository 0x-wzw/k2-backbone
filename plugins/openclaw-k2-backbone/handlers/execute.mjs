// K2 Execute tool handler
import { execSync } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const pluginDir = join(__dirname, '..');

export default async function handler(args, context) {
  const { spec_path } = args;
  const k2Path = context.config?.k2Path || '/home/ubuntu/.openclaw/workspace/k2-backbone';
  
  try {
    const result = execSync(
      `cd ${k2Path} && python3 -m k2_backbone.core.cli_v2 --spec "${spec_path}"`,
      { timeout: 120000, encoding: 'utf-8' }
    );
    return { content: [{ type: 'text', text: result.trim() }] };
  } catch (err) {
    return { content: [{ type: 'text', text: `Error: ${err.message}` }], isError: true };
  }
}