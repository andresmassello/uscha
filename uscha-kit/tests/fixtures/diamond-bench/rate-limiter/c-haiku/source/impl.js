function validateInput(input) {
  // Must be an object (not null, not array)
  if (typeof input !== 'object' || input === null || Array.isArray(input)) {
    return { valid: false };
  }

  // Must have capacity, refill, events
  if (!('capacity' in input) || !('refill' in input) || !('events' in input)) {
    return { valid: false };
  }

  const { capacity, refill, events } = input;

  // capacity and refill must be integers and non-negative
  if (!Number.isInteger(capacity) || capacity < 0) {
    return { valid: false };
  }
  if (!Number.isInteger(refill) || refill < 0) {
    return { valid: false };
  }

  // events must be an array
  if (!Array.isArray(events)) {
    return { valid: false };
  }

  // Each event must be exactly "tick" or "req"
  for (const event of events) {
    if (event !== 'tick' && event !== 'req') {
      return { valid: false };
    }
  }

  return { valid: true, capacity, refill, events };
}

function processEvents(capacity, refill, events) {
  let tokens = capacity;
  const log = [];

  for (const event of events) {
    if (event === 'req') {
      if (tokens >= 1) {
        log.push('allow');
        tokens--;
      } else {
        log.push('deny');
      }
    } else if (event === 'tick') {
      tokens = Math.min(capacity, tokens + refill);
    }
  }

  return { log, tokens };
}

function main() {
  const chunks = [];
  process.stdin.on('data', (chunk) => {
    chunks.push(chunk);
  });

  process.stdin.on('end', () => {
    const input = Buffer.concat(chunks).toString('utf-8');

    try {
      const parsed = JSON.parse(input);
      const validation = validateInput(parsed);

      if (!validation.valid) {
        process.stdout.write('ERROR\n');
        process.exit(0);
      }

      const result = processEvents(validation.capacity, validation.refill, validation.events);
      process.stdout.write(JSON.stringify(result) + '\n');
      process.exit(0);
    } catch (e) {
      // JSON parse error or other error
      process.stdout.write('ERROR\n');
      process.exit(0);
    }
  });
}

module.exports = {
  validateInput,
  processEvents,
  main
};

if (require.main === module) {
  main();
}
