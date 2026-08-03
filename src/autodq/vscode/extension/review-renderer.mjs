const PROTOCOL = 'autodq-review-v1';
const MESSAGE_TYPE = 'autodq.review.action';

const css = `
.autodq-review{box-sizing:border-box;color:var(--vscode-foreground);font-family:var(--vscode-font-family);font-size:13px;line-height:1.45;padding:8px 2px 18px}
.autodq-review *{box-sizing:border-box}
.autodq-review__header{align-items:flex-start;display:flex;gap:16px;justify-content:space-between;margin-bottom:12px}
.autodq-review h2{font-size:19px;margin:0 0 3px}.autodq-review h3{font-size:14px;margin:0}
.autodq-review__muted{color:var(--vscode-descriptionForeground);font-size:12px}
.autodq-review__metrics{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));margin:12px 0}
.autodq-review__metric{background:var(--vscode-editor-background);border:1px solid var(--vscode-panel-border);border-radius:8px;padding:9px 11px}
.autodq-review__metric span{color:var(--vscode-descriptionForeground);display:block;font-size:10px;letter-spacing:.04em;text-transform:uppercase}.autodq-review__metric strong{display:block;font-size:18px;margin-top:2px}
.autodq-review__notice{border-left:3px solid var(--vscode-textLink-foreground);margin:10px 0;padding:8px 10px}.autodq-review__notice--error{border-color:var(--vscode-errorForeground);color:var(--vscode-errorForeground)}
.autodq-review__toolbar{align-items:center;background:var(--vscode-editor-background);border:1px solid var(--vscode-panel-border);border-radius:9px;display:flex;flex-wrap:wrap;gap:7px;margin:12px 0;padding:9px}
.autodq-review button{background:var(--vscode-button-background);border:1px solid transparent;border-radius:4px;color:var(--vscode-button-foreground);cursor:pointer;font:inherit;padding:5px 10px}.autodq-review button:hover{background:var(--vscode-button-hoverBackground)}.autodq-review button.secondary{background:var(--vscode-button-secondaryBackground);color:var(--vscode-button-secondaryForeground)}.autodq-review button.secondary:hover{background:var(--vscode-button-secondaryHoverBackground)}.autodq-review button:disabled{cursor:not-allowed;opacity:.45}
.autodq-review input,.autodq-review textarea{background:var(--vscode-input-background);border:1px solid var(--vscode-input-border,var(--vscode-panel-border));border-radius:4px;color:var(--vscode-input-foreground);font:inherit;padding:6px 8px}.autodq-review input:focus,.autodq-review textarea:focus{border-color:var(--vscode-focusBorder);outline:1px solid var(--vscode-focusBorder)}
.autodq-review__reason{min-width:210px}.autodq-review__selection{color:var(--vscode-descriptionForeground);margin-right:auto;white-space:nowrap}
.autodq-review__table-wrap{border:1px solid var(--vscode-panel-border);border-radius:9px;max-height:430px;overflow:auto}.autodq-review table{border-collapse:collapse;width:100%}.autodq-review th,.autodq-review td{border-bottom:1px solid var(--vscode-panel-border);padding:7px 9px;text-align:left;vertical-align:top}.autodq-review th{background:var(--vscode-editor-background);font-size:11px;position:sticky;top:0;z-index:1}.autodq-review td:first-child,.autodq-review th:first-child{text-align:center;width:38px}
.autodq-review__badge{background:var(--vscode-badge-background);border-radius:999px;color:var(--vscode-badge-foreground);display:inline-block;font-size:10px;font-weight:700;padding:2px 7px;text-transform:capitalize}.autodq-review__badge--approved{background:#166534;color:#dcfce7}.autodq-review__badge--rejected{background:#991b1b;color:#fee2e2}.autodq-review__badge--pending{background:#854d0e;color:#fef9c3}
.autodq-review__columns{color:var(--vscode-textLink-foreground)}.autodq-review details{border-top:1px solid var(--vscode-panel-border);margin-top:12px;padding-top:10px}.autodq-review summary{cursor:pointer;font-weight:600}.autodq-review__details{color:var(--vscode-descriptionForeground);font-size:12px;margin-top:5px;max-width:620px}.autodq-review__details p{margin:4px 0}
.autodq-review td details{border:0;margin:0;padding:0}
.autodq-review__edit-grid{display:grid;gap:8px;grid-template-columns:minmax(110px,180px) minmax(260px,1fr);margin-top:10px}.autodq-review__edit-grid label{color:var(--vscode-descriptionForeground);font-size:11px}.autodq-review__edit-grid input,.autodq-review__edit-grid textarea{display:block;margin-top:3px;width:100%}.autodq-review__edit-grid textarea{font-family:var(--vscode-editor-font-family);min-height:78px}.autodq-review__edit-actions{align-items:end;display:flex;gap:8px}
.autodq-review__result{background:var(--vscode-textCodeBlock-background);border-radius:7px;margin-top:10px;max-height:350px;overflow:auto;padding:10px}.autodq-review__result pre{font-family:var(--vscode-editor-font-family);font-size:11px;margin:0;white-space:pre-wrap}
.autodq-review__result-card{background:var(--vscode-editor-background);border:1px solid var(--vscode-panel-border);border-radius:7px;margin-bottom:8px;padding:9px}.autodq-review__result-card:last-child{margin-bottom:0}.autodq-review__result-title{align-items:center;display:flex;gap:7px;margin-bottom:7px}.autodq-review__sample{margin-top:7px}.autodq-review__sample strong{display:block;font-size:11px;margin-bottom:4px}.autodq-review__sample table{background:var(--vscode-editor-background)}.autodq-review__sample th,.autodq-review__sample td{font-size:10px;padding:4px 6px}.autodq-review__key-values{display:grid;gap:5px;grid-template-columns:minmax(100px,180px) 1fr}.autodq-review__key-values dt{color:var(--vscode-descriptionForeground)}.autodq-review__key-values dd{margin:0;word-break:break-word}
.autodq-review__audit{margin-top:10px}.autodq-review__audit td{font-size:11px}.autodq-review code{font-family:var(--vscode-editor-font-family)}
@media(max-width:700px){.autodq-review__header{display:block}.autodq-review__edit-grid{grid-template-columns:1fr}.autodq-review__reason{min-width:100%;width:100%}}
`;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function button(label, action, secondary = false) {
  const node = element('button', secondary ? 'secondary' : '', label);
  node.type = 'button';
  node.dataset.action = action;
  return node;
}

function valueLabel(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return value.toLocaleString();
  return String(value);
}

function addMetric(container, label, value) {
  const card = element('div', 'autodq-review__metric');
  card.append(element('span', '', label), element('strong', '', valueLabel(value)));
  container.append(card);
}

function addDetail(parent, label, value) {
  if (value === null || value === undefined || value === '') return;
  const row = element('p');
  row.append(element('strong', '', `${label}: `), document.createTextNode(String(value)));
  parent.append(row);
}

function renderRecords(records) {
  const wrap = element('div', 'autodq-review__table-wrap autodq-review__sample');
  if (!records.length) {
    wrap.append(element('span', 'autodq-review__muted', 'No sample rows.'));
    return wrap;
  }
  const columns = [...new Set(records.flatMap((record) => Object.keys(record || {})))];
  const table = element('table');
  const head = element('thead');
  const headRow = element('tr');
  for (const column of columns) headRow.append(element('th', '', column));
  head.append(headRow);
  table.append(head);
  const body = element('tbody');
  for (const record of records) {
    const row = element('tr');
    for (const column of columns) row.append(element('td', '', valueLabel(record && record[column])));
    body.append(row);
  }
  table.append(body);
  wrap.append(table);
  return wrap;
}

function renderPreviewCard(preview) {
  const card = element('div', 'autodq-review__result-card');
  const title = element('div', 'autodq-review__result-title');
  title.append(
    element('strong', '', `Action ${preview.action_id}`),
    element('span', `autodq-review__badge autodq-review__badge--${preview.status || 'pending'}`, preview.status || 'pending'),
    element('span', 'autodq-review__muted', `${valueLabel(preview.affected_row_count)} affected row(s)`)
  );
  card.append(title);
  const facts = element('dl', 'autodq-review__key-values');
  for (const [label, value] of [['Issue', preview.issue_type], ['Strategy', preview.strategy]]) {
    facts.append(element('dt', '', label), element('dd', '', valueLabel(value)));
  }
  card.append(facts);
  if (preview.details && Object.keys(preview.details).length) {
    const detail = element('details');
    detail.append(element('summary', '', 'Preview details'));
    const pre = element('pre');
    pre.textContent = JSON.stringify(preview.details, null, 2);
    detail.append(pre);
    card.append(detail);
  }
  for (const [label, records] of [['Before sample', preview.before_sample], ['After sample', preview.after_sample]]) {
    const section = element('div', 'autodq-review__sample');
    section.append(element('strong', '', label), renderRecords(records || []));
    card.append(section);
  }
  return card;
}

function renderResult(container, result) {
  if (result === null || result === undefined) return;
  const box = element('div', 'autodq-review__result');
  const previews = Array.isArray(result.previews)
    ? result.previews
    : result.action_id !== undefined
      ? [result]
      : null;
  if (previews) {
    for (const preview of previews) box.append(renderPreviewCard(preview));
  } else if (result && typeof result === 'object' && !Array.isArray(result)) {
    const facts = element('dl', 'autodq-review__key-values');
    for (const [key, value] of Object.entries(result)) {
      facts.append(
        element('dt', '', key.replaceAll('_', ' ')),
        element('dd', '', typeof value === 'object' && value !== null ? JSON.stringify(value) : valueLabel(value))
      );
    }
    box.append(facts);
  } else {
    box.append(element('pre', '', JSON.stringify(result, null, 2)));
  }
  container.append(box);
}

function parseRowIndex(raw) {
  const value = raw.trim();
  if (/^-?\d+$/.test(value)) return Number.parseInt(value, 10);
  if (/^-?(?:\d+\.\d*|\d*\.\d+)$/.test(value)) return Number.parseFloat(value);
  return value;
}

function renderReview(context, outputItem, host) {
  const data = outputItem.json();
  host.replaceChildren();

  if (!data || data.protocol !== PROTOCOL) {
    host.append(element('p', 'autodq-review__notice autodq-review__notice--error', 'This cleaning review output is not compatible with the installed AutoDQ ADQL extension.'));
    return;
  }

  const root = element('section', 'autodq-review');
  const style = element('style');
  style.textContent = css;
  root.append(style);

  const header = element('div', 'autodq-review__header');
  const heading = element('div');
  heading.append(
    element('h2', '', 'Interactive Cleaning Review'),
    element('div', 'autodq-review__muted', 'Review actions here or use the equivalent ADQL commands. Changes remain in memory until CLEANING APPLY.')
  );
  header.append(heading);
  root.append(header);

  const summary = data.summary || {};
  const metrics = element('div', 'autodq-review__metrics');
  addMetric(metrics, 'Pending', summary.pending_count);
  addMetric(metrics, 'Approved', summary.approved_count);
  addMetric(metrics, 'Rejected', summary.rejected_count);
  addMetric(metrics, 'Working rows', summary.rows_working);
  addMetric(metrics, 'Manual changes', summary.changed);
  addMetric(metrics, 'Audit events', summary.audit_count);
  addMetric(metrics, 'Domain issues', summary.domain_violations);
  addMetric(metrics, 'Outliers', summary.outliers);
  root.append(metrics);

  const interaction = data.interaction || {};
  if (interaction.message) {
    root.append(element(
      'div',
      interaction.success === false ? 'autodq-review__notice autodq-review__notice--error' : 'autodq-review__notice',
      interaction.message
    ));
    renderResult(root, interaction.result);
  }

  const selected = new Set();
  const toolbar = element('div', 'autodq-review__toolbar');
  const selectedLabel = element('span', 'autodq-review__selection', '0 selected');
  const approve = button('Approve selected', 'approve');
  const preview = button('Preview selected', 'preview', true);
  const reason = element('input', 'autodq-review__reason');
  reason.type = 'text';
  reason.maxLength = 500;
  reason.placeholder = 'Optional rejection reason';
  reason.setAttribute('aria-label', 'Rejection reason');
  const reject = button('Reject selected', 'reject', true);
  const approveAll = button('Approve all', 'approve_all', true);
  const apply = button('Apply to CLEANED', 'apply');
  const refresh = button('Refresh', 'refresh', true);
  toolbar.append(selectedLabel, approve, preview, reason, reject, approveAll, apply, refresh);
  root.append(toolbar);

  const tableWrap = element('div', 'autodq-review__table-wrap');
  const table = element('table');
  const head = element('thead');
  const headRow = element('tr');
  const selectAllCell = element('th');
  const selectAll = element('input');
  selectAll.type = 'checkbox';
  selectAll.setAttribute('aria-label', 'Select all cleaning actions');
  selectAllCell.append(selectAll);
  headRow.append(selectAllCell);
  for (const label of ['ID', 'Issue', 'Strategy', 'Columns', 'Priority', 'Status', 'Details']) {
    headRow.append(element('th', '', label));
  }
  head.append(headRow);
  table.append(head);

  const body = element('tbody');
  const checkboxes = [];
  for (const action of data.actions || []) {
    const row = element('tr');
    const checkCell = element('td');
    const checkbox = element('input');
    checkbox.type = 'checkbox';
    checkbox.value = String(action.action_id);
    checkbox.setAttribute('aria-label', `Select action ${action.action_id}`);
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) selected.add(action.action_id);
      else selected.delete(action.action_id);
      updateSelection();
    });
    checkboxes.push(checkbox);
    checkCell.append(checkbox);
    row.append(checkCell);
    row.append(element('td', '', action.action_id));
    row.append(element('td', '', String(action.issue_type || '').replaceAll('_', ' ')));
    row.append(element('td', '', action.strategy));
    row.append(element('td', 'autodq-review__columns', (action.affected_columns || []).join(', ') || '—'));
    row.append(element('td', '', action.priority || '—'));
    const statusCell = element('td');
    statusCell.append(element('span', `autodq-review__badge autodq-review__badge--${action.status || 'pending'}`, action.status || 'pending'));
    row.append(statusCell);
    const detailCell = element('td');
    const details = element('details');
    details.append(element('summary', '', 'View'));
    const detailBody = element('div', 'autodq-review__details');
    addDetail(detailBody, 'Action', action.action);
    addDetail(detailBody, 'Reason', action.reason);
    addDetail(detailBody, 'Risk', action.risk);
    if (action.confidence !== null && action.confidence !== undefined) {
      addDetail(detailBody, 'Confidence', `${Math.round(Number(action.confidence) * 100)}%`);
    }
    details.append(detailBody);
    detailCell.append(details);
    row.append(detailCell);
    body.append(row);
  }
  table.append(body);
  tableWrap.append(table);
  root.append(tableWrap);

  function updateSelection() {
    selectedLabel.textContent = `${selected.size.toLocaleString()} selected`;
    approve.disabled = selected.size === 0;
    preview.disabled = selected.size === 0;
    reject.disabled = selected.size === 0;
    selectAll.checked = checkboxes.length > 0 && selected.size === checkboxes.length;
    selectAll.indeterminate = selected.size > 0 && selected.size < checkboxes.length;
  }

  selectAll.addEventListener('change', () => {
    selected.clear();
    for (const checkbox of checkboxes) {
      checkbox.checked = selectAll.checked;
      if (checkbox.checked) selected.add(Number(checkbox.value));
    }
    updateSelection();
  });

  const edit = element('details');
  edit.append(element('summary', '', 'Manual row edit'));
  const editGrid = element('div', 'autodq-review__edit-grid');
  const rowLabel = element('label', '', 'Row index');
  const rowIndex = element('input');
  rowIndex.placeholder = 'Example: 42';
  rowLabel.append(rowIndex);
  const changesLabel = element('label', '', 'Column changes (JSON object)');
  const changes = element('textarea');
  changes.placeholder = '{"Region": "North", "Customer_Age": 36}';
  changesLabel.append(changes);
  const editReasonLabel = element('label', '', 'Audit reason');
  const editReason = element('input');
  editReason.maxLength = 500;
  editReason.placeholder = 'Optional reason';
  editReasonLabel.append(editReason);
  const editActions = element('div', 'autodq-review__edit-actions');
  const editButton = button('Stage row edit', 'edit');
  const editError = element('span', 'autodq-review__muted');
  editActions.append(editButton, editError);
  editGrid.append(rowLabel, changesLabel, editReasonLabel, editActions);
  edit.append(editGrid);
  root.append(edit);

  const audit = data.audit_trail || [];
  if (audit.length) {
    const auditDetails = element('details');
    auditDetails.append(element('summary', '', `Recent audit trail (${audit.length})`));
    const auditWrap = element('div', 'autodq-review__table-wrap autodq-review__audit');
    const auditTable = element('table');
    const auditHead = element('thead');
    const auditHeadRow = element('tr');
    for (const label of ['ID', 'Event', 'Action', 'Row', 'Column', 'Reason', 'Time']) auditHeadRow.append(element('th', '', label));
    auditHead.append(auditHeadRow);
    auditTable.append(auditHead);
    const auditBody = element('tbody');
    for (const entry of audit.slice().reverse()) {
      const row = element('tr');
      for (const value of [entry.audit_id, entry.event_type, entry.action_id, entry.row_index, entry.column, entry.reason, entry.timestamp]) {
        row.append(element('td', '', valueLabel(value)));
      }
      auditBody.append(row);
    }
    auditTable.append(auditBody);
    auditWrap.append(auditTable);
    auditDetails.append(auditWrap);
    root.append(auditDetails);
  }

  const commands = element('details');
  commands.append(element('summary', '', 'Equivalent ADQL commands'));
  const commandList = element('div', 'autodq-review__details');
  for (const [name, command] of Object.entries(data.commands || {})) {
    const row = element('p');
    row.append(element('strong', '', `${name.replaceAll('_', ' ')}: `), element('code', '', command));
    commandList.append(row);
  }
  commands.append(commandList);
  root.append(commands);

  let busy = false;
  function setBusy(value) {
    busy = value;
    for (const control of root.querySelectorAll('button,input,textarea')) control.disabled = value;
    if (!value) updateSelection();
    if (value) selectedLabel.textContent = 'Working…';
  }

  function post(type, extra = {}) {
    if (busy) return;
    setBusy(true);
    context.postMessage({
      type: MESSAGE_TYPE,
      protocol: PROTOCOL,
      cell: data.cell && data.cell.number,
      interaction: { type, ...extra }
    });
  }

  approve.addEventListener('click', () => post('approve', { action_ids: [...selected] }));
  preview.addEventListener('click', () => post('preview', { action_ids: [...selected], max_rows: 5 }));
  reject.addEventListener('click', () => post('reject', { action_ids: [...selected], reason: reason.value }));
  approveAll.addEventListener('click', () => post('approve_all'));
  refresh.addEventListener('click', () => post('refresh'));
  apply.addEventListener('click', () => {
    const approved = Number(summary.approved_count || 0);
    const changed = Boolean(summary.changed);
    if (!approved && !changed) {
      selectedLabel.textContent = 'Approve an action or stage an edit first';
      return;
    }
    if (globalThis.confirm('Apply approved actions and staged edits to the CLEANED in-memory stage?')) post('apply');
  });
  editButton.addEventListener('click', () => {
    editError.textContent = '';
    if (!rowIndex.value.trim()) {
      editError.textContent = 'Enter a row index.';
      return;
    }
    let parsed;
    try {
      parsed = JSON.parse(changes.value);
    } catch (error) {
      editError.textContent = 'Changes must be valid JSON.';
      return;
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) || Object.keys(parsed).length === 0) {
      editError.textContent = 'Changes must be a non-empty JSON object.';
      return;
    }
    post('edit', { row_index: parseRowIndex(rowIndex.value), changes: parsed, reason: editReason.value });
  });

  updateSelection();
  host.append(root);
}

export function activate(context) {
  return {
    renderOutputItem(outputItem, element) {
      renderReview(context, outputItem, element);
    }
  };
}
