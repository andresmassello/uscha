#!/usr/bin/env node
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const script = path.join(__dirname, '..', 'uscha-kit', 'install-uscha.py');
const args = process.argv.slice(2);
const candidates = process.platform === 'win32'
  ? [ ['python', []], ['py', ['-3']] ]
  : [ ['python3', []], ['python', []] ];

let lastError = null;
for (const [cmd, prefix] of candidates) {
  const result = spawnSync(cmd, [...prefix, script, ...args], { stdio: 'inherit' });
  if (!result.error) {
    process.exit(result.status === null ? 1 : result.status);
  }
  if (result.error.code !== 'ENOENT') {
    lastError = result.error;
    break;
  }
  lastError = result.error;
}

console.error('[uscha] Python 3.8+ is required but was not found in PATH.');
if (lastError && lastError.message) {
  console.error(`[uscha] ${lastError.message}`);
}
process.exit(1);
