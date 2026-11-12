const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
// Unit tests use a minimal DOM/fetch double, not evidence of browser rendering.
function harness() {
  const elements = {}, pending = [];
  const document = {activeElement: null};
  class Element {
    constructor(tag = 'div') { this.tagName = tag; this.children = []; this.dataset = {}; this.value = ''; this.events = {}; }
    set textContent(value) { this.text = value; this.children = []; }
    get textContent() { return this.text || this.children.map(c => c.textContent).join(' '); }
    append(...nodes) { for (const n of nodes) { n.parentElement = this; this.children.push(n); } }
    replaceChildren(...nodes) {
      let active = document.activeElement;
      while (active) { if (active === this) { document.activeElement = null; break; } active = active.parentElement; }
      this.children = []; this.text = ''; this.append(...nodes);
    }
    setAttribute() {}
    addEventListener(name, fn) { this.events[name] = fn; }
    close() { this.open = false; }
    showModal() { this.open = true; }
    focus() { document.activeElement = this; }
    closest(tag) { let e = this; while (e && e.tagName !== tag) e = e.parentElement; return e; }
    querySelector(selector) {
      const action = selector.match(/data-action="([^"]+)"/)?.[1];
      const walk = e => e.dataset.action === action ? e : e.children.map(walk).find(Boolean);
      return walk(this);
    }
  }
  document.createElement = tag => new Element(tag);
  document.getElementById = id => elements[id] ||= new Element();
  const context = vm.createContext({document, fetch: () => new Promise(resolve => pending.push(resolve)),
    setInterval: () => 1, clearInterval: () => {}, Date, Error, console});
  vm.runInContext(fs.readFileSync('static/app.js', 'utf8'), context);
  const run = code => vm.runInContext(code, context);
  const response = {alerts: [{id:'fixture-A', title:'Unresolved P1', pipeline:'orders', severity:'P1', state:'New', version:1, updated_at:'2026-11-11T00:00:00Z'}], total:1, truncated:false};
  return {run, elements, pending, document, response};
}
test('late report response cannot repopulate after disconnect', async () => {
  const h = harness();
  const loading = h.run('token="unit-operator"; load()');
  h.run('disconnect()');
  h.pending.shift()({ok:true, json:async () => h.response});
  await loading;
  assert.equal(h.elements.rows.children.length, 0);
  assert.equal(h.elements.connection.textContent, 'Not connected');
});
test('old connection cannot overwrite a newer connection', async () => {
  const h = harness();
  const first = h.run('token="old"; load()');
  h.run('disconnect(); token="new"');
  const second = h.run('load()');
  const oldResolve = h.pending.shift(), newResolve = h.pending.shift();
  assert.equal(typeof newResolve, 'function');
  newResolve({ok:true, json:async () => ({alerts:[], total:0, truncated:false})});
  await second;
  oldResolve({ok:true, json:async () => h.response});
  await first;
  assert.equal(h.elements.rows.children.length, 0);
});
test('polling preserves focus on the same surviving action', async () => {
  const h = harness();
  const initial = h.run('token="unit-operator"; load()');
  h.pending.shift()({ok:true, json:async () => h.response});
  await initial;
  const firstButton = h.elements.rows.children[0].children[4].children[0].children[0];
  firstButton.focus();
  const refresh = h.run('load()');
  h.pending.shift()({ok:true, json:async () => h.response});
  await refresh;
  const newButton = h.elements.rows.children[0].children[4].children[0].children[0];
  assert.equal(h.document.activeElement, newButton);
  assert.notEqual(firstButton, newButton);
});
test('old unauthorized response cannot disconnect a newer session', async () => {
  const h = harness();
  const first = h.run('token="old"; load()');
  h.run('disconnect(); token="new"');
  const second = h.run('load()');
  const oldResolve = h.pending.shift(), newResolve = h.pending.shift();
  newResolve({ok:true, json:async () => h.response});
  await second;
  oldResolve({ok:false, status:401, json:async () => ({error:'Invalid token'})});
  await first;
  assert.equal(h.run('token'), 'new');
  assert.equal(h.elements.rows.children.length, 1);
});
test('changing to resolved history ignores a late active-report response', async () => {
  const h = harness();
  const first = h.run('token="operator"; load()');
  const second = h.run("switchView('resolved')");
  const activeResolve = h.pending.shift(), resolvedResolve = h.pending.shift();
  resolvedResolve({ok:true, json:async () => ({alerts:[], total:0, truncated:false})});
  await second;
  activeResolve({ok:true, json:async () => h.response});
  await first;
  assert.equal(h.elements.rows.children.length, 0);
  assert.equal(h.elements['report-title'].textContent, 'Resolved alert history');
});
test('resolved rows can open history but have no advance action', async () => {
  const h = harness();
  const item = {...h.response.alerts[0], state:'Resolved', title:'Retained resolved incident', version:5};
  const loading = h.run("token='operator'; view='resolved'; load()");
  h.pending.shift()({ok:true, json:async () => ({alerts:[item], total:1, truncated:false})});
  await loading;
  const row = h.elements.rows.children[0];
  assert.equal(row.children[4].children[0].children.length, 1);
  assert.equal(row.children[4].children[0].children[0].textContent, 'History');
  const opening = row.children[1].children[0].events.click();
  h.pending.shift()({ok:true, json:async () => ({alert:item,history:[{to_state:'Resolved',version:5,at:item.updated_at}]})});
  await opening;
  assert.equal(h.elements.detail.open, true);
  assert.match(h.elements['detail-content'].textContent, /Retained resolved incident/);
});
test('older detail response cannot overwrite the newly selected alert', async () => {
  const h = harness();
  const first = h.run("token='operator'; showHistory({id:'a'})");
  const second = h.run("showHistory({id:'b'})");
  const oldResolve = h.pending.shift(), newResolve = h.pending.shift();
  newResolve({ok:true,json:async () => ({alert:{...h.response.alerts[0],id:'b',title:'Selected B'},history:[]})});
  await second;
  oldResolve({ok:true,json:async () => ({alert:{...h.response.alerts[0],id:'a',title:'Old A'},history:[]})});
  await first;
  assert.match(h.elements['detail-content'].textContent,/Selected B/);
  assert.doesNotMatch(h.elements['detail-content'].textContent,/Old A/);
});
test('disconnect clears retained protected detail content', async () => {
  const h = harness();
  const loading = h.run("token='operator'; showHistory({id:'a'})");
  h.pending.shift()({ok:true,json:async () => ({alert:h.response.alerts[0],history:[]})});
  await loading;
  h.run('disconnect()');
  assert.equal(h.elements['detail-content'].textContent,'');
  assert.equal(h.elements.detail.open,false);
  assert.equal(h.document.activeElement,h.elements.token);
});
test('ordinary disconnect focuses the key field even without an open dialog', () => {
  const h = harness(); h.run("token='operator'; disconnect()");
  assert.equal(h.document.activeElement,h.elements.token);
  assert.equal(h.elements.session.hidden,false);
  assert.equal(h.elements.board.hidden,true);
});
test('removing a focused alert returns focus to the visible view heading', async () => {
  const h = harness();
  const heading = h.run("document.getElementById('view-heading')");
  const first = h.run("token='operator'; load()");
  h.pending.shift()({ok:true,json:async () => h.response}); await first;
  h.elements.rows.children[0].children[1].children[0].focus();
  const refresh = h.run('load()');
  h.pending.shift()({ok:true,json:async () => ({alerts:[],total:0,truncated:false})});
  await refresh;
  assert.equal(h.document.activeElement,heading);
});
test('first-load failure shows an error rather than a loading or all-clear state', async () => {
  const h = harness();
  const empty = h.run("document.getElementById('empty')");
  const loading = h.run("token='operator'; load()");
  h.pending.shift()({ok:false,status:503,json:async () => ({error:'Unavailable'})});
  await loading;
  assert.match(empty.textContent,/Report unavailable/);
  assert.doesNotMatch(empty.textContent,/Loading|All clear/);
});
test('disabling the clicked action cannot lose focus after its successful update', async () => {
  const h = harness();
  h.run("document.body=document.getElementById('unit-body')");
  const first = h.run("token='operator'; load()");
  h.pending.shift()({ok:true,json:async () => h.response}); await first;
  const button = h.elements.rows.children[0].querySelector('button[data-action="advance"]');
  button.focus();
  Object.defineProperty(button,'disabled',{set(value){
    if (value && h.document.activeElement === this) h.document.activeElement=h.document.body;
  }});
  const updating = h.run('advanceAlert(alerts[0],document.activeElement)');
  h.pending.shift()({ok:true,json:async () => ({alert:{...h.response.alerts[0],state:'Acknowledge',version:2}})});
  await new Promise(setImmediate);
  h.pending.shift()({ok:true,json:async () => ({...h.response,alerts:[{...h.response.alerts[0],state:'Acknowledge',version:2}]})});
  await updating;
  assert.equal(h.document.activeElement,
    h.elements.rows.children[0].querySelector('button[data-action="advance"]'));
});
test('server failure does not falsely claim an update was never applied', async () => {
  const h = harness();
  const first = h.run("token='operator'; load()");
  h.pending.shift()({ok:true,json:async () => h.response}); await first;
  const button = h.elements.rows.children[0].querySelector('button[data-action="advance"]');
  button.focus(); const update = h.run('advanceAlert(alerts[0],document.activeElement)');
  h.pending.shift()({ok:false,status:500,json:async () => ({error:'Internal error'})});
  await update;
  assert.match(h.elements.status.textContent,/could not be confirmed/);
  assert.doesNotMatch(h.elements.status.textContent,/not applied/);
});
