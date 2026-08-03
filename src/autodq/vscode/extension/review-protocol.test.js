'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const {
  REVIEW_MESSAGE_TYPE,
  REVIEW_PROTOCOL,
  normalizeReviewMessage
} = require('./review-protocol');

test('normalizes an allowlisted review action', () => {
  const result = normalizeReviewMessage({
    type: REVIEW_MESSAGE_TYPE,
    protocol: REVIEW_PROTOCOL,
    cell: 4,
    interaction: { type: 'APPROVE', action_ids: [1, 2] }
  });

  assert.equal(result.cell, 4);
  assert.equal(result.interaction.type, 'approve');
  assert.deepEqual(result.interaction.action_ids, [1, 2]);
});

test('rejects unknown actions and invalid cells', () => {
  assert.throws(() => normalizeReviewMessage({
    type: REVIEW_MESSAGE_TYPE,
    protocol: REVIEW_PROTOCOL,
    cell: 0,
    interaction: { type: 'approve' }
  }), /positive integer/);

  assert.throws(() => normalizeReviewMessage({
    type: REVIEW_MESSAGE_TYPE,
    protocol: REVIEW_PROTOCOL,
    cell: 1,
    interaction: { type: 'execute_python' }
  }), /Unsupported interactive review action/);
});
