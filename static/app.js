'use strict';
const $ = id => document.getElementById(id);
const nextState = {New: 'Acknowledge', Acknowledge: 'Investigating', Investigating: 'Monitoring', Monitoring: 'Resolved'};
let token = '', alerts = [], busy = false, timer = null, total = 0, epoch = 0, view = 'active', loaded = false;
function message(text, error = false) {
  $('status').textContent = text;
  $('status').className = error ? 'status error' : 'status';
}
function node(tag, text, cls) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (cls) result.className = cls;
  return result;
}
async function api(path, body) {
  const requestEpoch = epoch;
  const response = await fetch(path, {method: body ? 'POST' : 'GET', cache: 'no-store',
    headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'},
    body: body ? JSON.stringify(body) : undefined});
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401 && requestEpoch === epoch) {
      disconnect(); message('Access denied. Enter a valid operator access key.', true);
      $('connection').textContent = 'Authentication required';
    }
    throw new Error(result.error || `HTTP ${response.status}`);
  }
  return result;
}
function render() {
  const focused = document.activeElement;
  const focusId = focused?.closest('tr')?.dataset.id, focusAction = focused?.dataset.action;
  const query = $('search').value.toLowerCase(), severity = $('severity').value;
  const visible = alerts.filter(a => (!severity || a.severity === severity) &&
    `${a.title} ${a.pipeline}`.toLowerCase().includes(query));
  $('rows').replaceChildren();
  for (const alert of visible) {
    const row = node('tr'); row.dataset.id = alert.id;
    const severityCell = node('td'); severityCell.append(node('span', alert.severity, `severity ${alert.severity.toLowerCase()}`));
    const title = node('td'); const titleButton = node('button', alert.title, 'alert-title title-button');
    titleButton.type = 'button'; titleButton.dataset.action = 'detail';
    titleButton.setAttribute('aria-label', `Open alert: ${alert.title}`);
    titleButton.addEventListener('click', () => showHistory(alert));
    title.append(titleButton, node('span', alert.pipeline, 'pipeline'));
    const state = node('td'); state.append(node('span', alert.state, 'state'));
    const updated = node('td', new Date(alert.updated_at).toLocaleTimeString('en-GB'), 'updated-cell');
    const actions = node('td'), group = node('div', undefined, 'actions');
    const advance = node('button', nextState[alert.state] || 'Resolved');
    advance.type = 'button'; advance.dataset.action = 'advance';
    advance.setAttribute('aria-label', `${nextState[alert.state]}: ${alert.title}`);
    advance.addEventListener('click', () => advanceAlert(alert, advance));
    const history = node('button', 'History', 'history'); history.type = 'button'; history.dataset.action = 'history';
    history.setAttribute('aria-label', `History: ${alert.title}`);
    history.addEventListener('click', () => showHistory(alert));
    if (alert.state !== 'Resolved') group.append(advance);
    group.append(history); actions.append(group);
    row.append(severityCell, title, state, updated, actions); $('rows').append(row);
  }
  if (focusId && focusAction) {
    const row = [...$('rows').children].find(r => r.dataset.id === focusId);
    row?.querySelector(`button[data-action="${focusAction}"]`)?.focus();
  }
  $('empty').hidden = visible.length > 0;
  if (!visible.length) {
    $('empty').replaceChildren(node('div', token ? (!loaded ? 'Loading report…' : alerts.length ? 'No matching alerts.' : view === 'active' ? 'All clear. No active alerts.' : 'No resolved alerts yet.') : 'Your report is ready.'),
      node('span', token ? 'Resolved alerts remain available in retained history.' : 'Unlock the board with your pilot access key.'));
  }
  $('total').textContent = token && loaded ? alerts.length : '—';
  if (view === 'active') $('nav-count').textContent = token && loaded ? alerts.length : '—';
  for (const s of ['P1', 'P2', 'P3', 'P4']) $(''+s).textContent = token && loaded ? alerts.filter(a => a.severity === s).length : '—';
  $('report-info').textContent = token && loaded ? `${visible.length} shown · ${alerts.length} loaded · ${total} ${view} in store` : 'No data loaded';
  $('report-title').textContent = view === 'active' ? 'Active alert report' : 'Resolved alert history';
  $('scope-label').textContent = view === 'active' ? 'LOADED ACTIVE' : 'LOADED RESOLVED';
  for (const scope of ['active', 'resolved']) {
    const button = $(`${scope}-view`); button.className = scope === view ? 'nav-current' : '';
    button.setAttribute('aria-pressed', String(scope === view));
  }
}
async function load() {
  if (!token || busy) return;
  busy = true; const requestEpoch = epoch;
  try {
    const result = await api(`/api/alerts?scope=${view}`);
    if (requestEpoch !== epoch) return;
    alerts = result.alerts; total = result.total; loaded = true;
    $('truncated').hidden = !result.truncated;
    render(); $('connection').textContent = 'Live · polling every 2s';
    $('updated').textContent = `Synchronized ${new Date().toLocaleTimeString('en-GB')}`;
    message('Report synchronized with the live API.');
  } catch (error) {
    if (requestEpoch !== epoch) return;
    message(`Report unavailable: ${error.message}. Displayed data may be stale.`, true);
    $('connection').textContent = 'Connection error';
  } finally { if (requestEpoch === epoch) busy = false; }
}
async function advanceAlert(alert, button) {
  if (!token || busy) return;
  busy = true; button.disabled = true; const requestEpoch = epoch;
  try {
    await api(`/api/alerts/${alert.id}/state`, {state: nextState[alert.state], version: alert.version});
    if (requestEpoch !== epoch) return;
    busy = false; await load();
  } catch (error) {
    if (requestEpoch !== epoch) return;
    message(`Update not applied: ${error.message}`, true);
  } finally { if (requestEpoch === epoch) busy = false; button.disabled = false; }
}
async function showHistory(alert) {
  if (!token) { message('Unlock the board before opening history.', true); return; }
  const requestEpoch = epoch;
  $('detail-content').replaceChildren(node('p', 'Loading retained history…'));
  if (!$('detail').open) $('detail').showModal();
  try {
    const result = await api(`/api/alerts/${encodeURIComponent(alert.id)}`), current = result.alert;
    if (requestEpoch !== epoch) return;
    const list = node('ol');
    for (const h of result.history) list.append(node('li', `${h.to_state} · v${h.version} · ${new Date(h.at).toLocaleString('en-GB')}`));
    $('detail-content').replaceChildren(node('p', current.title), node('code', current.id),
      node('p', `${current.pipeline} · ${current.severity} · ${current.state}`), list);
  } catch (error) { if (requestEpoch !== epoch) return; $('detail-content').replaceChildren(node('p', error.message)); }
}
function disconnect() {
  epoch++; busy = false; token = ''; alerts = []; total = 0; loaded = false; $('nav-count').textContent = '—'; clearInterval(timer); timer = null;
  $('token').value = ''; $('truncated').hidden = true;
  $('connection').textContent = 'Not connected'; $('updated').textContent = 'Not synchronized';
  $('detail').close(); render(); message('Board locked. Enter an access key to load alerts.');
}
$('session').addEventListener('submit', async event => {
  event.preventDefault(); const entered = $('token').value; disconnect(); token = entered;
  clearInterval(timer); await load();
  if (token) timer = setInterval(load, 2000);
});
$('refresh').addEventListener('click', () => token ? load() : message('Unlock the board with your pilot access key first.'));
$('disconnect').addEventListener('click', disconnect);
$('search').addEventListener('input', render); $('severity').addEventListener('change', render);
$('close-detail').addEventListener('click', () => $('detail').close());

function switchView(scope) {
  epoch++; busy = false; view = scope; alerts = []; total = 0; loaded = false;
  $('truncated').hidden = true; render();
  if (token) { message('Loading report…'); return load(); }
}
$('active-view').addEventListener('click', () => switchView('active'));
$('resolved-view').addEventListener('click', () => switchView('resolved'));
