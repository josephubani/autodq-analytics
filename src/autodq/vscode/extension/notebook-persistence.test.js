'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  OUTPUT_CACHE_END,
  OUTPUT_CACHE_START,
  appendOutputCache,
  cellFingerprint,
  decodeCellOutputs,
  encodeCellOutputs,
  extractOutputCache
} = require('./notebook-persistence');

test('output cache round-trips text, HTML, and binary output', () => {
  const source = [
    '#!/usr/bin/env autodq',
    '# %% [Dataset]',
    'DATASET "sales.csv";',
    ''
  ].join('\n');
  const outputs = [
    {
      metadata: { title: 'Preview' },
      items: [
        { mime: 'text/plain', data: Buffer.from('5,002 rows') },
        { mime: 'text/html', data: Buffer.from('<b>5,002 rows</b>') },
        { mime: 'image/png', data: Buffer.from([137, 80, 78, 71]) }
      ]
    }
  ];
  const encoded = encodeCellOutputs(outputs);
  const fingerprint = cellFingerprint('code', 'Dataset', 'DATASET "sales.csv";');
  const saved = appendOutputCache(source, {
    cells: [{ index: 0, fingerprint, outputs: encoded }]
  });
  const restored = extractOutputCache(saved);
  const decoded = decodeCellOutputs(restored.cache.cells[0].outputs);

  assert.match(saved, new RegExp(OUTPUT_CACHE_START));
  assert.match(saved, new RegExp(OUTPUT_CACHE_END));
  assert.equal(restored.source, source);
  assert.equal(restored.cache.cells[0].fingerprint, fingerprint);
  assert.equal(decoded[0].items[0].data.toString(), '5,002 rows');
  assert.equal(decoded[0].items[1].data.toString(), '<b>5,002 rows</b>');
  assert.deepEqual([...decoded[0].items[2].data], [137, 80, 78, 71]);
});

test('corrupt output cache is left in source instead of being discarded', () => {
  const source = [
    '# %% [Cell]',
    'HEAD 5;',
    OUTPUT_CACHE_START,
    '# this-is-not-base64-json',
    OUTPUT_CACHE_END,
    ''
  ].join('\n');
  const restored = extractOutputCache(source);

  assert.equal(restored.source, source);
  assert.equal(restored.cache, null);
});

test('cell fingerprint changes with executable source', () => {
  const first = cellFingerprint('code', 'Rows', 'HEAD 5;');
  const same = cellFingerprint('code', 'Rows', 'HEAD 5;\n\n');
  const changed = cellFingerprint('code', 'Rows', 'HEAD 10;');

  assert.equal(first, same);
  assert.notEqual(first, changed);
});
