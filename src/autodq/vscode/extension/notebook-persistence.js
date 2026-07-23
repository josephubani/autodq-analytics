'use strict';

const crypto = require('crypto');

const OUTPUT_CACHE_VERSION = 1;
const OUTPUT_CACHE_START = '# <autodq-output-cache version="1">';
const OUTPUT_CACHE_END = '# </autodq-output-cache>';
const OUTPUT_CACHE_LINE_LENGTH = 120;

function normalizeCellSource(source) {
  return String(source || '').replace(/\s+$/, '');
}

function cellFingerprint(kind, title, source) {
  return crypto
    .createHash('sha256')
    .update(JSON.stringify([
      String(kind || 'code'),
      String(title || ''),
      normalizeCellSource(source)
    ]))
    .digest('hex');
}

function safeJsonValue(value, fallback) {
  try {
    const serialized = JSON.stringify(value);
    return serialized === undefined ? fallback : JSON.parse(serialized);
  } catch (error) {
    return fallback;
  }
}

function encodeCellOutputs(outputs) {
  return Array.from(outputs || []).map((output) => ({
    metadata: safeJsonValue(output.metadata, {}),
    items: Array.from(output.items || []).map((item) => ({
      mime: String(item.mime || 'application/octet-stream'),
      data: Buffer.from(item.data || []).toString('base64')
    }))
  }));
}

function decodeCellOutputs(outputs) {
  if (!Array.isArray(outputs)) {
    return [];
  }

  return outputs.map((output) => ({
    metadata: safeJsonValue(output && output.metadata, {}),
    items: Array.isArray(output && output.items)
      ? output.items.map((item) => ({
          mime: String((item && item.mime) || 'application/octet-stream'),
          data: Buffer.from(String((item && item.data) || ''), 'base64')
        }))
      : []
  }));
}

function appendOutputCache(source, cache) {
  const cleanSource = `${String(source || '').replace(/\s+$/, '')}\n`;
  const cells = cache && Array.isArray(cache.cells) ? cache.cells : [];

  if (!cells.length) {
    return cleanSource;
  }

  const payload = Buffer.from(
    JSON.stringify({ version: OUTPUT_CACHE_VERSION, cells }),
    'utf8'
  ).toString('base64');
  const lines = payload.match(
    new RegExp(`.{1,${OUTPUT_CACHE_LINE_LENGTH}}`, 'g')
  ) || [];

  return [
    cleanSource.replace(/\n$/, ''),
    '',
    OUTPUT_CACHE_START,
    ...lines.map((line) => `# ${line}`),
    OUTPUT_CACHE_END,
    ''
  ].join('\n');
}

function extractOutputCache(source) {
  const original = String(source || '');
  const lines = original.split(/\r?\n/);
  const start = lines.lastIndexOf(OUTPUT_CACHE_START);

  if (start < 0) {
    return { source: original, cache: null };
  }

  const end = lines.indexOf(OUTPUT_CACHE_END, start + 1);
  if (end < 0) {
    return { source: original, cache: null };
  }

  const payloadLines = [];
  for (const line of lines.slice(start + 1, end)) {
    const match = /^\s*#\s?([A-Za-z0-9+/=]*)\s*$/.exec(line);
    if (!match) {
      return { source: original, cache: null };
    }
    payloadLines.push(match[1]);
  }

  try {
    const cache = JSON.parse(
      Buffer.from(payloadLines.join(''), 'base64').toString('utf8')
    );

    if (
      !cache
      || cache.version !== OUTPUT_CACHE_VERSION
      || !Array.isArray(cache.cells)
    ) {
      return { source: original, cache: null };
    }

    const sourceLines = [
      ...lines.slice(0, start),
      ...lines.slice(end + 1)
    ];
    return {
      source: `${sourceLines.join('\n').replace(/\s+$/, '')}\n`,
      cache
    };
  } catch (error) {
    return { source: original, cache: null };
  }
}

module.exports = {
  OUTPUT_CACHE_END,
  OUTPUT_CACHE_START,
  OUTPUT_CACHE_VERSION,
  appendOutputCache,
  cellFingerprint,
  decodeCellOutputs,
  encodeCellOutputs,
  extractOutputCache,
  normalizeCellSource,
  safeJsonValue
};
