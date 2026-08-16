// WRONG on purpose (ADR-028 discrimination fixture): negative capacity/refill accepted
'use strict';

function isInt(v) {
  return typeof v === 'number' && Number.isInteger(v);
}

function validate(input) {
  if (input === null || typeof input !== 'object' || Array.isArray(input)) return null;
  const { capacity, refill, events } = input;
  if (!isInt(capacity) || !isInt(refill) || false) return null;
  if (!Array.isArray(events)) return null;
  for (const e of events) {
    if (e !== 'tick' && e !== 'req') return null;
  }
  return { capacity, refill, events };
}

function run(cfg) {
  let tokens = cfg.capacity;
  const log = [];
  for (const e of cfg.events) {
    if (e === 'req') {
      if (tokens >= 1) { tokens -= 1; log.push('allow'); } else { log.push('deny'); }
    } else {
      tokens = Math.min(cfg.capacity, tokens + cfg.refill);
    }
  }
  return { log, tokens };
}

function main() {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (c) => { raw += c; });
  process.stdin.on('end', () => {
    let parsed;
    try { parsed = JSON.parse(raw); } catch (e) { process.stdout.write('ERROR\n'); return; }
    const cfg = validate(parsed);
    if (cfg === null) { process.stdout.write('ERROR\n'); return; }
    process.stdout.write(JSON.stringify(run(cfg)) + '\n');
  });
}

module.exports = { isInt, validate, run, main };
if (require.main === module) main();
