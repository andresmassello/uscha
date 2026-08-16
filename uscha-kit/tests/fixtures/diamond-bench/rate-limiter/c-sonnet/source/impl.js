'use strict';

function isInt(n) {
  return typeof n === 'number' && Number.isInteger(n);
}

function run(input) {
  if (input === null || typeof input !== 'object' || Array.isArray(input)) {
    return null;
  }
  const { capacity, refill, events } = input;

  if (!isInt(capacity) || capacity < 0) return null;
  if (!isInt(refill) || refill < 0) return null;
  if (!Array.isArray(events)) return null;
  for (const ev of events) {
    if (ev !== 'tick' && ev !== 'req') return null;
  }

  let tokens = capacity;
  const log = [];

  for (const ev of events) {
    if (ev === 'req') {
      if (tokens >= 1) {
        tokens -= 1;
        log.push('allow');
      } else {
        log.push('deny');
      }
    } else if (ev === 'tick') {
      tokens = Math.min(capacity, tokens + refill);
    }
  }

  return { log, tokens };
}

function main() {
  const chunks = [];
  process.stdin.on('data', (chunk) => chunks.push(chunk));
  process.stdin.on('end', () => {
    const raw = chunks.join('');
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (e) {
      console.log('ERROR');
      return;
    }
    const result = run(parsed);
    if (result === null) {
      console.log('ERROR');
    } else {
      console.log(JSON.stringify(result));
    }
  });
}

module.exports = { run, isInt, main };

if (require.main === module) {
  main();
}
