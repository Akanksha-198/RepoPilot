import { useEffect, useState, useCallback } from 'react';
import { api } from '../api.js';
import { useToast } from './Toast.jsx';
import Diff from './Diff.jsx';

export default function GitPanel({ repoId, refreshKey, task }) {
  const toast = useToast();
  const base = `/repos/${repoId}/git`;
  const [status, setStatus] = useState(null);
  const [last, setLast] = useState(null);
  const [diff, setDiff] = useState(null);
  const [busy, setBusy] = useState('');
  const [pr, setPr] = useState({ title: '', body: '' });

  const load = useCallback(async () => {
    try {
      setStatus(await api.get(`${base}/status`));
      const l = await api.get(`${base}/last-commit`);
      setLast(l);
      setPr((p) => p.title ? p : {
        title: l.message || '',
        body: `Automated change by RepoPilot.\n\nBranch: ${l.branch}\nLast commit: ${l.hash} — ${l.message}\n\nPlease review the diff before merging.`,
      });
    } catch (e) { setStatus({ error: e.message }); }
  }, [base]);

  useEffect(() => { load(); }, [load, refreshKey]);

  async function run(name, path, okMsg, body) {
    setBusy(name);
    try {
      const out = await api.post(`${base}/${path}`, body);
      if (out.success === false) toast(out.message || 'Action failed.', 'err');
      else toast(out.url ? `${okMsg} ${out.url}` : okMsg);
      await load();
    } catch (e) { toast(e.message, 'err'); }
    setBusy('');
  }

  const onFeature = last?.has_commit && !['main', 'master', ''].includes(last.branch);

  return (
    <details className="glass pad">
      <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
        Git · {status?.branch || '…'} {status && !status.error && <span className={`chip ${status.clean ? 'ok' : 'warn'}`}>{status.clean ? 'clean' : 'uncommitted changes'}</span>}
      </summary>
      <div className="stack" style={{ marginTop: 16 }}>
        {status?.error && <div className="banner warn">{status.error}</div>}
        {status && !status.error && !status.clean && (
          <div className="small muted">
            {['staged', 'modified', 'untracked'].map((k) => status[k]?.length ? <div key={k}><b>{k}:</b> {status[k].join(', ')}</div> : null)}
          </div>
        )}
        <div className="row">
          <button className="btn" onClick={async () => { try { setDiff((await api.get(`${base}/diff`)).diff || 'No unstaged changes.'); } catch (e) { toast(e.message, 'err'); } }}>View git diff</button>
          <button className="btn ghost" disabled={busy === 'ib'} onClick={() => run('ib', 'ignore-backups', 'Backup files are no longer tracked.')}>Stop tracking backup files</button>
        </div>
        {diff && <Diff text={diff} />}

        {onFeature && (
          <div className="stack">
            <div><b>Last commit:</b> <code>{last.hash}</code> — {last.message} <span className={`chip ${last.pushed ? 'ok' : 'warn'}`}>{last.pushed ? 'on GitHub' : 'local only'}</span></div>
            {!last.pushed ? (
              <div className="row">
                <button className="btn primary" disabled={!!busy} onClick={() => run('push', 'push', 'Pushed to GitHub.')}>{busy === 'push' ? 'Pushing…' : 'Push to GitHub'}</button>
                <button className="btn ghost" disabled={!!busy} onClick={() => confirm('Undo the last local commit? Your changes stay in the working tree.') && run('undo', 'undo', 'Last commit undone.')}>Undo last commit</button>
              </div>
            ) : (
              <>
                <div className="row">
                  <button className="btn ghost" disabled={!!busy} onClick={() => confirm('Add a new commit that reverses the last one?') && run('rev', 'revert', 'Revert commit created.')}>Revert last commit</button>
                </div>
                <div className="stack">
                  <h3>Open a pull request</h3>
                  <label>Title<input value={pr.title} onChange={(e) => setPr({ ...pr, title: e.target.value })} /></label>
                  <label>Description<textarea value={pr.body} onChange={(e) => setPr({ ...pr, body: e.target.value })} /></label>
                  <button className="btn primary" disabled={!!busy || pr.title.trim().length < 3} onClick={() => run('pr', 'pr', 'Pull request ready →', pr)}>{busy === 'pr' ? 'Creating…' : 'Create pull request'}</button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </details>
  );
}
