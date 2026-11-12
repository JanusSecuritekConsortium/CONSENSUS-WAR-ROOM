"""The single page the phone opens. Everything shown from the server is placed with
textContent, never as HTML, so a proposal's text cannot inject markup."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>CONSENSUS</title>
<style>
  :root { --bg:#0b0f12; --panel:#141b20; --line:#2a3a44; --text:#d7e3ea; --muted:#8aa0ad; --accent:#f5a623;
          --ok:#5fd38d; --bad:#ff6b5e; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:16px/1.45 ui-monospace,Consolas,Menlo,monospace; }
  main { max-width:640px; margin:0 auto; padding:16px; }
  h1 { font-size:18px; letter-spacing:.12em; color:var(--accent); margin:8px 0 16px; }
  h2 { font-size:13px; letter-spacing:.1em; color:var(--muted); margin:24px 0 8px; }
  .panel { background:var(--panel); border:1px solid var(--line); padding:14px; margin-bottom:12px; }
  label { display:block; font-size:12px; color:var(--muted); margin:10px 0 4px; }
  input, select, textarea, button { width:100%; font:inherit; color:var(--text); background:var(--bg);
          border:1px solid var(--line); padding:12px; border-radius:0; }
  textarea { min-height:140px; resize:vertical; }
  button { background:var(--accent); color:#111; border-color:var(--accent); font-weight:bold; margin-top:12px; }
  button.quiet { background:transparent; color:var(--muted); border-color:var(--line); font-weight:normal; }
  button:disabled { opacity:.5; }
  .row { display:flex; gap:8px; align-items:center; justify-content:space-between; }
  .row button { width:auto; margin:0; padding:8px 12px; }
  .note { color:var(--muted); font-size:13px; min-height:1.4em; margin-top:8px; overflow-wrap:anywhere; }
  .bad { color:var(--bad); } .ok { color:var(--ok); }
  .ticket { border-top:1px solid var(--line); padding:10px 0; }
  .ticket:first-child { border-top:0; }
  .ticket .q { overflow-wrap:anywhere; }
  .ticket .meta { color:var(--muted); font-size:12px; margin-top:4px; }
  .verdict { font-weight:bold; margin-top:6px; }
  .reason { font-size:14px; margin-top:4px; overflow-wrap:anywhere; }
  [hidden] { display:none !important; }
</style>
</head>
<body>
<main>
  <h1>CONSENSUS</h1>

  <section id="login" class="panel" hidden>
    <label for="name">Operator</label>
    <select id="name"></select>
    <label for="pin">PIN</label>
    <input id="pin" type="password" autocomplete="current-password">
    <button id="signin">Sign in</button>
    <div id="loginNote" class="note"></div>
  </section>

  <section id="desk" hidden>
    <div class="row">
      <div id="who" class="note"></div>
      <button id="signout" class="quiet">Sign out</button>
    </div>
    <div class="panel">
      <label for="question">Proposal for the tribunal</label>
      <textarea id="question" maxlength="4000"></textarea>
      <button id="submit">Submit to tribunal</button>
      <div id="submitNote" class="note"></div>
    </div>
    <div class="row">
      <h2>RECENT</h2>
      <button id="refresh" class="quiet">Refresh</button>
    </div>
    <div id="tickets" class="panel"></div>
  </section>
</main>
<script>
const $ = id => document.getElementById(id);
const api = async (path, options = {}) => {
  const response = await fetch('/phone/v1' + path, {
    credentials: 'same-origin',
    headers: options.body ? {'Content-Type': 'application/json'} : {},
    ...options,
  });
  let data = {};
  try { data = await response.json(); } catch (error) {}
  return {ok: response.ok, status: response.status, data};
};
const note = (id, text, kind) => { const el = $(id); el.textContent = text || ''; el.className = 'note ' + (kind || ''); };
const STATUS = {queued: 'Waiting to start', running: 'Deliberating', finished: 'Finished', failed: 'Failed'};

function ticketView(item) {
  const box = document.createElement('div'); box.className = 'ticket';
  const add = (cls, text) => { const el = document.createElement('div'); el.className = cls; el.textContent = text; box.appendChild(el); return el; };
  add('q', item.question);
  let meta = (STATUS[item.status] || item.status) + ' · ' + (item.submitted_by || 'unknown') + ' · ' + (item.requested_at || '').replace('T', ' ').slice(0, 16);
  if (item.status === 'running' && item.elapsed_minutes != null) meta += ' · ' + item.elapsed_minutes + ' min';
  add('meta', meta);
  if (item.result) {
    const confidence = item.result.confidence != null ? ' (' + Math.round(item.result.confidence * 100) + '%)' : '';
    add('verdict', 'Verdict: ' + (item.result.verdict || '?') + confidence);
    if (item.result.reason) add('reason', item.result.reason);
  }
  if (item.error) add('reason bad', item.error);
  return box;
}

async function loadTickets() {
  const {ok, status, data} = await api('/proposals');
  if (status === 401) return showLogin();
  const list = $('tickets'); list.textContent = '';
  if (!ok) { list.textContent = 'Could not load.'; return; }
  if (!data.proposals.length) { list.textContent = 'Nothing submitted from the phone yet.'; return; }
  data.proposals.forEach(item => list.appendChild(ticketView(item)));
}

async function showLogin() {
  $('desk').hidden = true; $('login').hidden = false;
  const {ok, data} = await api('/operators');
  const select = $('name'); select.textContent = '';
  (ok ? data.operators : []).forEach(name => { const option = document.createElement('option'); option.textContent = name; select.appendChild(option); });
}

async function showDesk(name) {
  $('login').hidden = true; $('desk').hidden = false; $('pin').value = '';
  $('who').textContent = 'Signed in: ' + name;
  await loadTickets();
}

$('signin').onclick = async () => {
  note('loginNote', 'Checking...');
  const {ok, data} = await api('/login', {method: 'POST', body: JSON.stringify({name: $('name').value, pin: $('pin').value})});
  if (ok) { note('loginNote', ''); showDesk(data.name); } else { note('loginNote', data.detail || 'Sign-in failed.', 'bad'); $('pin').value = ''; }
};
$('pin').addEventListener('keydown', event => { if (event.key === 'Enter') $('signin').click(); });
$('signout').onclick = async () => { await api('/logout', {method: 'POST'}); showLogin(); };
$('refresh').onclick = loadTickets;
$('submit').onclick = async () => {
  const question = $('question').value.trim();
  if (!question) return note('submitNote', 'Write a proposal first.', 'bad');
  $('submit').disabled = true; note('submitNote', 'Sending...');
  const {ok, status, data} = await api('/proposals', {method: 'POST', body: JSON.stringify({question})});
  $('submit').disabled = false;
  if (status === 401) return showLogin();
  if (ok) { $('question').value = ''; note('submitNote', 'Submitted. Local models can take up to an hour.', 'ok'); loadTickets(); }
  else note('submitNote', data.detail || 'Could not submit.', 'bad');
};

(async () => { const {ok, data} = await api('/me'); ok ? showDesk(data.name) : showLogin(); })();
setInterval(() => { if (!$('desk').hidden && document.visibilityState === 'visible') loadTickets(); }, 30000);
</script>
</body>
</html>
"""
