"use strict";

function isJsonObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isNonNegativeInteger(value) {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isValidEvent(value) {
  return value === "tick" || value === "req";
}

function isValidConfig(value) {
  if (!isJsonObject(value)) {
    return false;
  }

  if (!Object.prototype.hasOwnProperty.call(value, "capacity")) {
    return false;
  }

  if (!Object.prototype.hasOwnProperty.call(value, "refill")) {
    return false;
  }

  if (!Object.prototype.hasOwnProperty.call(value, "events")) {
    return false;
  }

  if (!isNonNegativeInteger(value.capacity) || !isNonNegativeInteger(value.refill)) {
    return false;
  }

  if (!Array.isArray(value.events)) {
    return false;
  }

  return value.events.every(isValidEvent);
}

function parseInput(text) {
  try {
    return JSON.parse(text);
  } catch (_error) {
    return null;
  }
}

function runBucket(config) {
  let tokens = config.capacity;
  const log = [];

  for (const event of config.events) {
    if (event === "tick") {
      tokens = Math.min(config.capacity, tokens + config.refill);
      continue;
    }

    if (tokens >= 1) {
      tokens -= 1;
      log.push("allow");
    } else {
      log.push("deny");
    }
  }

  return { log, tokens };
}

function formatOutput(value) {
  const parsed = typeof value === "string" ? parseInput(value) : value;

  if (!isValidConfig(parsed)) {
    return "ERROR";
  }

  return JSON.stringify(runBucket(parsed));
}

function main() {
  const fs = require("fs");
  const input = fs.readFileSync(0, "utf8");
  process.stdout.write(formatOutput(input) + "\n");
}

module.exports = {
  isJsonObject,
  isNonNegativeInteger,
  isValidEvent,
  isValidConfig,
  parseInput,
  runBucket,
  formatOutput,
  main,
};

if (require.main === module) {
  main();
}
