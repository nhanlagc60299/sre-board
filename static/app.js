'use strict';
const $ = id => document.getElementById(id);
const nextState = {New: 'Acknowledge', Acknowledge: 'Investigating', Investigating: 'Monitoring', Monitoring: 'Resolved'};
let token = '', alerts = [], busy = false, timer = null, total = 0;
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
  const response = await fetch(path, {method: body ? 'POST' : 'GET', cache: 'no-store',
    headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'},
    body: body ? JSON.stringify(body) : undefined});
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401) disconnect();
    throw new Error(result.error || `HTTP ${response.status}`);
  }
  return result;
}
function render() {
  const query = $('search').value.toLowerCase(), severity = $('severity').value;
  const visible = alerts.filter(a => (!severity || a.severity === severity) &&
    `${a.title} ${a.pipeline}`.toLowerCase().includes(query));
  $('rows').replaceChildren();
  for (const alert of visible) {
    const row = node('tr'); row.dataset.id = alert.id;
    const severityCell = node('td'); severityCell.append(node('span', alert.severity, `severity ${alert.severity.toLowerCase()}`));
    const title = node('td'); title.append(node('span', alert.title, 'alert-title'), node('span', alert.pipeline, 'pipeline'));
    const state = node('td'); state.append(node('span', alert.state, 'state'));
    const updated = node('td', new Date(alert.updated_at).toLocaleTimeString('en-GB'), 'updated-cell');
    const actions = node('td'), group = node('div', undefined, 'actions');
    const advance = node('button', nextState[alert.state] || 'Resolved');
    advance.type = 'button'; advance.dataset.action = 'advance';
    advance.setAttribute('aria-label', `${nextState[alert.state]}: ${alert.title}`);
    advance.addEventListener('click', () => advanceAlert(alert, advance));
    const history = node('button', 'History', 'history'); history.type = 'button';
    history.setAttribute('aria-label', `History: ${alert.title}`);
    history.addEventListener('click', () => showHistory(alert));
    group.append(advance, history); actions.append(group);
    row.append(severityCell, title, state, updated, actions); $('rows').append(row);
  }
  $('empty').hidden = visible.length > 0;
  if (!visible.length) {
    $('empty').replaceChildren(node('div', token ? (alerts.length ? 'No matching alerts.' : 'All clear. No active alerts.') : 'Your report is ready.'),
      node('span', token ? 'Resolved alerts remain available in retained history.' : 'Connect with an operator token to retrieve alerts.'));
  }
  $('total').textContent = token ? alerts.length : '—';
  $('nav-count').textContent = token ? alerts.length : '—';
  for (const s of ['P1', 'P2', 'P3', 'P4']) $(''+s).textContent = token ? alerts.filter(a => a.severity === s).length : '—';
  $('report-info').textContent = token ? `${visible.length} shown · ${alerts.length} loaded · ${total} active in store` : 'No data loaded';
}
async function load() {
  if (!token || busy) return;
  busy = true;
  try {
    const result = await api('/api/alerts');
    alerts = result.alerts; total = result.total;
    $('truncated').hidden = !result.truncated;
    render(); $('connection').textContent = 'Live · polling every 2s';
    $('updated').textContent = `Synchronized ${new Date().toLocaleTimeString('en-GB')}`;
    message('Report synchronized with the live API.');
  } catch (error) {
    message(`Report unavailable: ${error.message}. Displayed data may be stale.`, true);
    $('connection').textContent = 'Connection error';
  } finally { busy = false; }
}
async function advanceAlert(alert, button) {
  if (!token || busy) return;
  busy = true; button.disabled = true;
  try {
    await api(`/api/alerts/${alert.id}/state`, {state: nextState[alert.state], version: alert.version});
    busy = false; await load();
  } catch (error) {
    message(`Update not applied: ${error.message}`, true);
  } finally { busy = false; button.disabled = false; }
}
async function showHistory(alert) {
  $('detail-content').replaceChildren(node('p', 'Loading retained history…'));
  if (!$('detail').open) $('detail').showModal();
  try {
    const result = await api(`/api/alerts/${alert.id}`), current = result.alert;
    const list = node('ol');
    for (const h of result.history) list.append(node('li', `${h.to_state} · v${h.version} · ${new Date(h.at).toLocaleString('en-GB')}`));
    $('detail-content').replaceChildren(node('p', current.title), node('code', current.id),
      node('p', `${current.pipeline} · ${current.severity} · ${current.state}`), list);
  } catch (error) { $('detail-content').replaceChildren(node('p', error.message)); }
}
function disconnect() {
  token = ''; alerts = []; total = 0; clearInterval(timer); timer = null;
  $('token').value = ''; $('truncated').hidden = true;
  $('connection').textContent = 'Not connected'; $('updated').textContent = 'Not synchronized';
  $('detail').close(); render(); message('Disconnected. Enter a token to load alerts.');
}
$('session').addEventListener('submit', async event => {
  event.preventDefault(); token = $('token').value; $('token').value = '';
  clearInterval(timer); await load();
  if (token) timer = setInterval(load, 2000);
});
$('refresh').addEventListener('click', () => token ? load() : message('Enter an operator token first.'));
$('disconnect').addEventListener('click', disconnect);
$('search').addEventListener('input', render); $('severity').addEventListener('change', render);
$('close-detail').addEventListener('click', () => $('detail').close());
