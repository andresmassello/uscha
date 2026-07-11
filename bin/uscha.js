#!/usr/bin/env node
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const script = path.join(__dirname, '..', 'uscha-kit', 'install-uscha.py');
const args = process.argv.slice(2);
const candidates = process.platform === 'win32'
  ? [ ['python', []], ['py', ['-3']] ]
  : [ ['python3', []], ['python', []] ];

function supportsPython38(command, prefix) {
  const result = spawnSync(command, [...prefix, '--version'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  if (result.error || result.status !== 0) return false;

  const output = `${result.stdout || ''}\n${result.stderr || ''}`;
  const match = output.match(/Python\s+(\d+)\.(\d+)/i);
  return match !== null && (Number(match[1]) > 3
    || (Number(match[1]) === 3 && Number(match[2]) >= 8));
}

let lastError = null;
for (const [command, prefix] of candidates) {
  if (!supportsPython38(command, prefix)) continue;

  const result = spawnSync(command, [...prefix, script, ...args], { stdio: 'inherit' });
  if (result.error) {
    lastError = result.error;
    break;
  }
  process.exit(result.status === null ? 1 : result.status);
}

console.error('[uscha] Python 3.8+ is required but was not found in PATH.');
if (lastError && lastError.message) {
  console.error(`[uscha] ${lastError.message}`);
}
process.exit(1);
