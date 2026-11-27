'use strict';
// Local development configuration matches the imported Keycloak realm.
const issuer = 'http://127.0.0.1:8088/realms/gtm-dev';
const clientId = 'gtm-workspace-web';
const redirectUri = 'http://127.0.0.1:8010/workspace-app';
let accessToken = null;
let organizations = [];
let sessionVersion = 0;
let accountRequestVersion = 0;
const $ = id => document.getElementById(id);
const b64 = bytes => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
function message(text, error = false) { const box = $('message'); box.textContent = text; box.classList.toggle('error', error); }
function randomString() { return b64(crypto.getRandomValues(new Uint8Array(32))); }

async function signIn() {
  if (location.origin !== 'http://127.0.0.1:8010') { message('Open this workspace at http://127.0.0.1:8010/workspace-app.', true); return; }
  const verifier = randomString(), state = randomString();
  const challenge = b64(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))));
  sessionStorage.setItem('gtm_pkce_verifier', verifier);
  sessionStorage.setItem('gtm_pkce_state', state);
  const params = new URLSearchParams({client_id:clientId, redirect_uri:redirectUri, response_type:'code', scope:'openid', state, code_challenge:challenge, code_challenge_method:'S256'});
  location.assign(issuer + '/protocol/openid-connect/auth?' + params);
}

async function finishSignIn() {
  const params = new URLSearchParams(location.search);
  if (!params.has('code') && !params.has('error')) return false;
  const code = params.get('code'), returnedState = params.get('state');
  const expectedState = sessionStorage.getItem('gtm_pkce_state'), verifier = sessionStorage.getItem('gtm_pkce_verifier');
  sessionStorage.removeItem('gtm_pkce_state'); sessionStorage.removeItem('gtm_pkce_verifier');
  history.replaceState(null, '', location.pathname);
  if (!code || !expectedState || !verifier || returnedState !== expectedState) throw new Error('Sign-in could not be verified. Please try again.');
  const body = new URLSearchParams({grant_type:'authorization_code', client_id:clientId, code, code_verifier:verifier, redirect_uri:redirectUri});
  const response = await fetch(issuer + '/protocol/openid-connect/token', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body});
  if (!response.ok) throw new Error('Sign-in failed. Please try again.');
  const data = await response.json();
  if (!data.access_token) throw new Error('No access token was returned.');
  accessToken = data.access_token; // Memory only: never persist tokens in web storage.
  return true;
}

async function api(path, options = {}) {
  const token = accessToken;
  const response = await fetch(path, {...options, headers:{...options.headers, Authorization:'Bearer ' + token}});
  if (token !== accessToken) throw new Error('Your workspace session changed.');
  if (response.status === 401) { accessToken = null; $('workspace').hidden = true; $('sign-in').hidden = false; $('sign-out').hidden = true; throw new Error('Your session has expired. Please sign in again.'); }
  if (response.status === 403) throw new Error('You do not have permission for this action.');
  if (!response.ok) throw new Error('The workspace could not complete your request. Try again.');
  return response.json();
}

async function loadAccounts() {
  const organization = $('organization').value;
  if (!organization) return;
  const requestVersion = ++accountRequestVersion, currentSession = sessionVersion;
  $('account-status').textContent = 'Loading…';
  const accounts = await api('/workspace/organizations/' + encodeURIComponent(organization) + '/accounts');
  if (requestVersion !== accountRequestVersion || currentSession !== sessionVersion || organization !== $('organization').value) return;
  const container = $('account-list'); container.replaceChildren();
  if (!accounts.length) { container.className = 'table-wrap empty'; container.textContent = 'No accounts yet. Add a fictional company to get started.'; }
  else {
    container.className = 'table-wrap';
    const table = document.createElement('table'), head = document.createElement('thead'), tr = document.createElement('tr'), th = document.createElement('th'), body = document.createElement('tbody');
    th.textContent = 'Account name'; tr.append(th); head.append(tr); table.append(head);
    for (const account of accounts) { const row = document.createElement('tr'), cell = document.createElement('td'); cell.textContent = account.name; row.append(cell); body.append(row); }
    table.append(body); container.append(table);
  }
  $('account-status').textContent = accounts.length + (accounts.length === 1 ? ' account' : ' accounts');
  const selected = organizations.find(item => item.id === organization);
  const canWrite = selected && ['owner','admin','member'].includes(selected.role);
  $('account-name').disabled = !canWrite; $('account-form').querySelector('button').disabled = !canWrite;
}

async function loadWorkspace() {
  const currentSession = sessionVersion;
  const result = await api('/workspace/organizations');
  if (currentSession !== sessionVersion) return;
  organizations = result;
  const select = $('organization'); select.replaceChildren();
  for (const org of organizations) { const option = document.createElement('option'); option.value = org.id; option.textContent = org.name; select.append(option); }
  $('sign-in').hidden = true; $('sign-out').hidden = false;
  if (!organizations.length) { $('workspace').hidden = true; message('This user has no workspace membership. Ask an administrator to add one.'); return; }
  $('workspace').hidden = false; message('Signed in. Use fictional data in this development workspace.');
  await loadAccounts();
}

$('sign-in').addEventListener('click', () => signIn().catch(() => message('Could not start sign-in. Check Keycloak and try again.', true)));
$('sign-out').addEventListener('click', () => { sessionVersion++; accountRequestVersion++; accessToken = null; organizations = []; $('organization').replaceChildren(); $('account-list').replaceChildren(); $('account-status').textContent = ''; $('account-name').value = ''; $('workspace').hidden = true; $('sign-in').hidden = false; $('sign-out').hidden = true; message('Signed out of this workspace. Your identity-provider session may still be active.'); });
$('organization').addEventListener('change', () => loadAccounts().catch(err => message(err.message, true)));
$('account-form').addEventListener('submit', async event => {
  event.preventDefault(); const input = $('account-name'), name = input.value.trim();
  if (!name) { message('Enter an account name.', true); return; }
  const button = event.currentTarget.querySelector('button'); button.disabled = true;
  try { await api('/workspace/organizations/' + encodeURIComponent($('organization').value) + '/accounts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name})}); input.value = ''; message('Account added.'); await loadAccounts(); }
  catch(err) { message(err.message, true); }
  finally { const selected = organizations.find(item => item.id === $('organization').value); button.disabled = !selected || !['owner','admin','member'].includes(selected.role); }
});
finishSignIn().then(signedIn => signedIn && loadWorkspace()).catch(err => message(err.message, true));
