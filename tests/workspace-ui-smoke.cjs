const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() { this.value = ''; this.textContent = ''; this.children = []; this.hidden = false; this.listeners = {}; this.classList = {toggle() {}}; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  replaceChildren(...children) { this.children = children; this.textContent = ''; }
  append(...children) { this.children.push(...children); }
  querySelector() { return this.button ||= new Element(); }
}
const elements = {};
const element = id => elements[id] ||= new Element();
const pending = [];
const context = vm.createContext({
  document: {getElementById: element, createElement: () => new Element()},
  location: {search: '', pathname: '/workspace-app', origin: 'http://127.0.0.1:8010'},
  sessionStorage: {getItem() {return null;}, removeItem() {}, setItem() {}},
  fetch: url => new Promise(resolve => pending.push({url, resolve})),
  URLSearchParams, TextEncoder, console,
});
vm.runInContext(fs.readFileSync('workspace_ui/app.js', 'utf8'), context);
const response = data => ({status: 200, ok: true, json: async () => data});

(async () => {
  vm.runInContext("accessToken='token'; organizations=[{id:'a', role:'member'}, {id:'b', role:'member'}]", context);
  element('organization').value = 'a';
  const first = vm.runInContext('loadAccounts()', context);
  element('organization').value = 'b';
  const second = vm.runInContext('loadAccounts()', context);
  assert(pending[0].url.endsWith('/a/accounts'));
  assert(pending[1].url.endsWith('/b/accounts'));
  pending[1].resolve(response([{name: 'Second account'}]));
  await second;
  pending[0].resolve(response([{name: 'Stale first account'}]));
  await first;
  const table = element('account-list').children[0];
  assert.equal(table.children[1].children[0].children[0].textContent, 'Second account');
  assert.equal(element('account-status').textContent, '1 account');

  const third = vm.runInContext('loadAccounts()', context).catch(error => error);
  element('sign-out').listeners.click();
  pending[2].resolve(response([{name: 'Private account'}]));
  await third;
  assert.equal(element('workspace').hidden, true);
  assert.equal(element('account-list').children.length, 0);
  assert.equal(vm.runInContext('accessToken', context), null);
  console.log('Workspace ignores stale organization responses and clears account data on sign-out.');
})().catch(error => { console.error(error); process.exit(1); });
