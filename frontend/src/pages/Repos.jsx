import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import { api } from '../api.js';
import { useToast } from '../components/Toast.jsx';

export default function Repos() {
  const toast = useToast();
  const [repos, setRepos] = useState(null);
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setRepos((await api.get('/repos')).repos); } catch (e) { toast(e.message, 'err'); }
  }, [toast]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!repos?.some((r) => r.status === 'cloning')) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [repos, load]);

  async function add(e) {
    e.preventDefault(); setBusy(true);
    try { await api.post('/repos', { github_url: url }); setUrl(''); await load(); }
    catch (x) { toast(x.message, 'err'); }
    setBusy(false);
  }
  async function remove(r) {
    if (!confirm(`Remove ${r.name} and its local copy?`)) return;
    try { await api.del(`/repos/${r.id}`); await load(); } catch (x) { toast(x.message, 'err'); }
  }

  return (
    <div className="stack">
      <div><h2>Repositories</h2><p className="muted">Add a GitHub repository. RepoPilot clones it, scans it and indexes the code so it can answer with real context.</p></div>
      <form className="glass pad row" onSubmit={add}>
        <input style={{ flex: 1, minWidth: 240 }} placeholder="https://github.com/owner/repo" value={url} onChange={(e) => setUrl(e.target.value)} required aria-label="GitHub repository URL" />
        <button className="btn primary" disabled={busy}>Add repository</button>
      </form>
      {repos === null && <div className="spinner" aria-label="Loading" />}
      {repos?.length === 0 && <div className="glass pad"><h3>No repositories yet</h3><p className="muted">Paste a GitHub URL above to get started. Private repositories need a token in Settings first.</p></div>}
      <div className="grid">
        {repos?.map((r) => {
          const body = (
            <>
              <div className="row between"><div className="title">{r.name}</div>
                <span className={`chip ${r.status === 'ready' ? 'ok' : r.status === 'failed' ? 'bad' : 'warn'}`}>{r.status === 'cloning' ? 'Indexing…' : r.status}</span></div>
              {r.status === 'ready' && <div className="muted small">{r.scan?.file_count ?? 0} files · {r.chunk_count} code chunks</div>}
              {r.status === 'failed' && <div className="small" style={{ color: 'var(--bad)' }}>{r.error}</div>}
            </>
          );
          return r.status === 'ready'
            ? <div key={r.id} className="glass card"><Link to={`/repos/${r.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'grid', gap: 10 }}>{body}</Link>
                <button className="btn ghost danger" onClick={() => remove(r)} aria-label={`Remove ${r.name}`}><Trash2 size={15} /> Remove</button></div>
            : <div key={r.id} className="glass card">{body}{r.status === 'failed' && <button className="btn ghost danger" onClick={() => remove(r)}><Trash2 size={15} /> Remove</button>}</div>;
        })}
      </div>
    </div>
  );
}
