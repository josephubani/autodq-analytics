'use strict';

const REVIEW_MIME = 'application/vnd.autodq.review+json';
const REVIEW_PROTOCOL = 'autodq-review-v1';
const REVIEW_RENDERER_ID = 'autodq-adql-review-renderer';
const REVIEW_MESSAGE_TYPE = 'autodq.review.action';
const REVIEW_ACTIONS = new Set([
  'refresh',
  'approve',
  'approve_all',
  'reject',
  'preview',
  'apply',
  'edit'
]);

function normalizeReviewMessage(message) {
  if (!message || typeof message !== 'object') {
    throw new Error('Interactive review message must be an object.');
  }
  if (message.type !== REVIEW_MESSAGE_TYPE || message.protocol !== REVIEW_PROTOCOL) {
    throw new Error('Unsupported interactive review message.');
  }

  const cell = Number(message.cell);
  if (!Number.isInteger(cell) || cell < 1) {
    throw new Error('Interactive review cell must be a positive integer.');
  }

  const interaction = message.interaction;
  if (!interaction || typeof interaction !== 'object' || Array.isArray(interaction)) {
    throw new Error('Interactive review action must be an object.');
  }

  const action = String(interaction.type || '').trim().toLowerCase();
  if (!REVIEW_ACTIONS.has(action)) {
    throw new Error(`Unsupported interactive review action: ${action || '(empty)'}`);
  }

  return {
    cell,
    interaction: { ...interaction, type: action }
  };
}

module.exports = {
  REVIEW_MIME,
  REVIEW_PROTOCOL,
  REVIEW_RENDERER_ID,
  REVIEW_MESSAGE_TYPE,
  normalizeReviewMessage
};
