'use strict';
// Public client configuration is supplied by the same-origin API.
let issuer, clientId;
const redirectUri = location.origin + '/workspace-app';
async function loadConfig() {
  if (issuer && clientId) return;
  const allowedLoopback = location.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname);
  if (location.protocol !== 'https:' && !allowedLoopback) throw new Error('Secure connection required.');
  const response = await fetch('/workspace-config', {cache:'no-store'});
  if (!response.ok) throw new Error('Workspace sign-in is not configured.');
  const config = await response.json();
  issuer = config.issuer; clientId = config.client_id;
}
let accessToken = null;
let organizations = [];
let sessionVersion = 0;
let accountRequestVersion = 0;
let crmRequestVersion = 0;
let dealRequestVersion = 0;
let workspaceScanVersion = 0;
const $ = id => document.getElementById(id);
const b64 = bytes => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
function message(text, error = false) { const box = $('message'); box.textContent = text; box.classList.toggle('error', error); }
function randomString() { return b64(crypto.getRandomValues(new Uint8Array(32))); }

async function signIn() {
  await loadConfig();
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
  await loadConfig();
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
  const accountSelect = $('deal-account'); accountSelect.replaceChildren();
  for (const account of accounts) { const option = document.createElement('option'); option.value = account.id; option.textContent = account.name; accountSelect.append(option); }
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
  $('deal-submit').disabled = !canWrite || !accounts.length;
}

async function loadDeals() {
  const organization = $('organization').value;
  if (!organization) return;
  const version = ++dealRequestVersion, currentSession = sessionVersion;
  $('deals-status').textContent = 'Loading…';
  const deals = await api('/workspace/organizations/' + encodeURIComponent(organization) + '/deals');
  if (version !== dealRequestVersion || currentSession !== sessionVersion || organization !== $('organization').value) return;
  const container = $('deal-list'); container.replaceChildren();
  if (!deals.length) { container.className = 'table-wrap empty'; container.textContent = 'No deals yet.'; }
  else {
    container.className = 'table-wrap';
    const table = document.createElement('table'), body = document.createElement('tbody');
    for (const deal of deals) { const row = document.createElement('tr'); for (const value of [deal.name, deal.company, deal.stage, deal.owner_name || 'Unassigned']) { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); } body.append(row); }
    table.append(body); container.append(table);
  }
  $('deals-status').textContent = deals.length + (deals.length === 1 ? ' deal' : ' deals');
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
  $('workspace').hidden = false; message('Signed in. Use fictional data in this workspace preview.');
  await loadAccounts();
  if (currentSession === sessionVersion) await loadDeals();
}

$('sign-in').addEventListener('click', () => signIn().catch(() => message('Could not start sign-in. Check the workspace configuration and try again.', true)));
$('sign-out').addEventListener('click', () => { sessionVersion++; accountRequestVersion++; crmRequestVersion++; dealRequestVersion++; workspaceScanVersion++; accessToken = null; organizations = []; $('organization').replaceChildren(); $('account-list').replaceChildren(); $('deal-account').replaceChildren(); $('deal-list').replaceChildren(); $('account-status').textContent = ''; $('deals-status').textContent = ''; for (const id of ['account-name','deal-name','deal-stage','deal-owner','deal-value','deal-email','deal-phone','deal-contact-date','deal-stage-date']) $(id).value = ''; $('crm-result').textContent = ''; $('crm-workspace-result').textContent = ''; $('workspace').hidden = true; $('sign-in').hidden = false; $('sign-out').hidden = true; message('Signed out of this workspace. Your identity-provider session may still be active.'); });
$('organization').addEventListener('change', () => { accountRequestVersion++; dealRequestVersion++; crmRequestVersion++; workspaceScanVersion++; $('account-list').replaceChildren(); $('deal-account').replaceChildren(); $('deal-list').replaceChildren(); $('account-status').textContent = ''; $('deals-status').textContent = ''; for (const id of ['account-name','deal-name','deal-stage','deal-owner','deal-value','deal-email','deal-phone','deal-contact-date','deal-stage-date']) $(id).value = ''; $('crm-result').textContent = ''; $('crm-workspace-result').textContent = ''; $('deal-submit').disabled = true; Promise.all([loadAccounts(), loadDeals()]).catch(err => message(err.message, true)); });
$('crm-scan').addEventListener('click', async () => {
  const organization = $('organization').value, currentSession = sessionVersion, requestVersion = ++crmRequestVersion;
  if (!organization || !accessToken) return;
  const button = $('crm-scan'); button.disabled = true;
  $('crm-result').textContent = 'Running sample scan…';
  try {
    const result = await api('/workspace/organizations/' + encodeURIComponent(organization) + '/crm/sample-scan', {method:'POST'});
    if (currentSession !== sessionVersion || requestVersion !== crmRequestVersion || organization !== $('organization').value) return;
    if (!result.completed || result.error) throw new Error('The sample scan could not be completed.');
    $('crm-result').textContent = `Scanned ${result.total_deals_count} sample deal(s). ${result.problematic_deals_count} need attention; ${result.total_alerts_count} issues found. No notifications sent.`;
  } catch (err) {
    if (currentSession === sessionVersion && requestVersion === crmRequestVersion && organization === $('organization').value) $('crm-result').textContent = 'The sample scan could not be completed. Try again.';
  } finally { button.disabled = false; }
});
$('account-form').addEventListener('submit', async event => {
  event.preventDefault(); const input = $('account-name'), name = input.value.trim();
  if (!name) { message('Enter an account name.', true); return; }
  const button = event.currentTarget.querySelector('button'); button.disabled = true;
  try { await api('/workspace/organizations/' + encodeURIComponent($('organization').value) + '/accounts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name})}); input.value = ''; message('Account added.'); await loadAccounts(); }
  catch(err) { message(err.message, true); }
  finally { const selected = organizations.find(item => item.id === $('organization').value); button.disabled = !selected || !['owner','admin','member'].includes(selected.role); }
});
$('deal-form').addEventListener('submit', async event => {
  event.preventDefault(); const organization = $('organization').value, currentSession = sessionVersion;
  const value = $('deal-value').value;
  const body = {account_id:$('deal-account').value, name:$('deal-name').value.trim(), stage:$('deal-stage').value.trim(), owner_name:$('deal-owner').value.trim(), deal_value:value === '' ? null : value, contact_email:$('deal-email').value.trim() || null, contact_phone:$('deal-phone').value.trim() || null, last_contact_date:$('deal-contact-date').value, stage_changed_date:$('deal-stage-date').value};
  $('deal-submit').disabled = true;
  try {
    await api('/workspace/organizations/' + encodeURIComponent(organization) + '/deals', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    if (currentSession !== sessionVersion || organization !== $('organization').value) return;
    for (const id of ['deal-name','deal-stage','deal-owner','deal-value','deal-email','deal-phone','deal-contact-date','deal-stage-date']) $(id).value = '';
    message('Deal added.'); await loadDeals();
  } catch (err) { if (currentSession === sessionVersion && organization === $('organization').value) message('Could not add the deal. Check the fields and try again.', true); }
  finally { const selected = organizations.find(item => item.id === $('organization').value); $('deal-submit').disabled = !selected || !['owner','admin','member'].includes(selected.role) || !$('deal-account').value; }
});
$('crm-workspace-scan').addEventListener('click', async () => {
  const organization = $('organization').value, currentSession = sessionVersion, version = ++workspaceScanVersion;
  if (!organization || !accessToken) return;
  const button = $('crm-workspace-scan'); button.disabled = true; $('crm-workspace-result').textContent = 'Scanning workspace deals…';
  try {
    const result = await api('/workspace/organizations/' + encodeURIComponent(organization) + '/crm/scan', {method:'POST'});
    if (currentSession !== sessionVersion || version !== workspaceScanVersion || organization !== $('organization').value) return;
    if (!result.completed || result.error) throw new Error('Scan failed');
    $('crm-workspace-result').textContent = `Scanned ${result.total_deals_count} deal(s). ${result.problematic_deals_count} need attention; ${result.total_alerts_count} issues found. No notifications sent.`;
    for (const notification of Object.values(result.owner_notifications || {})) for (const alert of notification.alerts || []) { const item = document.createElement('p'); item.textContent = `${alert.deal_name}: ${alert.recommended_action}`; $('crm-workspace-result').append(item); }
  } catch (err) { if (currentSession === sessionVersion && version === workspaceScanVersion && organization === $('organization').value) $('crm-workspace-result').textContent = 'Could not run the scan. Add a deal and try again.'; }
  finally { button.disabled = false; }
});
finishSignIn().then(signedIn => signedIn && loadWorkspace()).catch(err => message(err.message, true));
