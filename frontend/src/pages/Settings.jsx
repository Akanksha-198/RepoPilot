import { useState } from 'react';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useToast } from '../components/Toast.jsx';

export default function Settings() {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const [token, setToken] = useState('');

  async function save(e) {
    e.preventDefault();
    try { await api.put('/settings/github-token', { token }); setToken(''); await refresh(); toast('GitHub token saved (encrypted).'); }
    catch (x) { toast(x.message, 'err'); }
  }
  async function remove() {
    try { await api.del('/settings/github-token'); await refresh(); toast('GitHub token removed.'); } catch (x) { toast(x.message, 'err'); }
  }

  return (
    <div className="stack">
      <h2>Settings</h2>
      <form className="glass pad stack" onSubmit={save}>
        <h3>GitHub token</h3>
        <p className="muted">Needed to clone private repositories, push branches and open pull requests. Create a fine-grained token with <b>Contents</b> and <b>Pull requests</b> read/write on the repositories you use. It is stored encrypted and never shown again.</p>
        <div className="row"><span className={`chip ${user.has_github_token ? 'ok' : ''}`}>{user.has_github_token ? 'Token saved' : 'No token'}</span></div>
        <label>New token<input type="password" value={token} onChange={(e) => setToken(e.target.value)} autoComplete="off" placeholder="github_pat_…" required minLength={20} /></label>
        <div className="row">
          <button className="btn primary">Save token</button>
          {user.has_github_token && <button type="button" className="btn ghost danger" onClick={remove}>Remove token</button>}
        </div>
      </form>
    </div>
  );
}
