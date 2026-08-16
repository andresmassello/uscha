'use strict';

// Token-bucket rate limiter.
// Reads one JSON object from stdin, replays its events through the bucket,
// prints one line: the result object, or exactly ERROR on malformed input.

const ALLOW = 'allow';
const DENY = 'deny';
const TICK = 'tick';
const REQ = 'req';

/**
 * A JSON integer: a finite, integral number. Booleans are not integers,
 * and neither are non-integral numbers (JSON has no separate int type).
 */
function isNonNegativeInteger(value) {
  return (
    typeof value === 'number' &&
    Number.isInteger(value) &&
    value >= 0
  );
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * Validate the parsed input. Returns the normalized config, or null when the
 * input is malformed. Validation is total: nothing is processed until the whole
 * input has been accepted, so a malformed event never yields a partial log.
 */
function validate(input) {
  if (!isPlainObject(input)) return null;

  if (!Object.prototype.hasOwnProperty.call(input, 'capacity')) return null;
  if (!Object.prototype.hasOwnProperty.call(input, 'refill')) return null;
  if (!Object.prototype.hasOwnProperty.call(input, 'events')) return null;

  const { capacity, refill, events } = input;

  if (!isNonNegativeInteger(capacity)) return null;
  if (!isNonNegativeInteger(refill)) return null;
  if (!Array.isArray(events)) return null;

  for (const event of events) {
    if (event !== TICK && event !== REQ) return null;
  }

  return { capacity, refill, events };
}

/**
 * Replay the events through the bucket.
 * INV-RL-CLAMP-01: tokens never leave [0, capacity] — a req at zero tokens is
 * denied (no decrement below 0) and a tick is clamped at capacity.
 */
function run(config) {
  const { capacity, refill, events } = config;
  let tokens = capacity;
  const log = [];

  for (const event of events) {
    if (event === REQ) {
      if (tokens >= 1) {
        tokens -= 1;
        log.push(ALLOW);
      } else {
        log.push(DENY);
      }
    } else {
      tokens = Math.min(capacity, tokens + refill);
    }
  }

  return { log, tokens };
}

/**
 * Full pipeline over raw stdin text: parse, validate, replay.
 * Returns the result object, or null when the input is malformed.
 */
function process(raw) {
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    return null;
  }

  const config = validate(parsed);
  if (config === null) return null;

  return run(config);
}

function readStdin() {
  const fs = require('fs');
  try {
    return fs.readFileSync(0, 'utf8');
  } catch (err) {
    return '';
  }
}

function main() {
  const result = process(readStdin());
  if (result === null) {
    console.log('ERROR');
  } else {
    console.log(JSON.stringify(result));
  }
}

module.exports = {
  isNonNegativeInteger,
  isPlainObject,
  validate,
  run,
  process,
  main,
};

if (require.main === module) {
  main();
}
