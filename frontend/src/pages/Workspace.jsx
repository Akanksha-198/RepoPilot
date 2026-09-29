import { useEffect, useState, useCallback, useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { api } from '../api.js';
import { useToast } from '../components/Toast.jsx';
import Diff from '../components/Diff.jsx';
import GitPanel from '../components/GitPanel.jsx';

const BUSY = { analyzing: 'Reading your repository and preparing a change…', applying: 'Applying the change, backing up the file and validating…',
  repairing: 'Analyzing the failure and preparing a repair…', repair_applying: 'Applying the repair and validating again…' };

function stageIndex(t) {
  if (!t) return -1;
  if (t.commit_hash) return 4;
  if (t.validation_passed) return 3;
  if (['applied', 'repaired', 'repairing', 'repair_review', 'repair_applying', 'repair_failed', 'applying'].includes(t.status)) return 2;
  if (t.status === 'analyzing') return 0;
  return 1;
}

function ResultBanner({ title, ok, rows }) {
  return (
    <div className={`banner ${ok === true ? 'ok' : ok === false ? 'warn' : 'bad'}`}>
      <b>{title}</b>
      {rows.filter(Boolean).map(([k, v]) => <div key={k} className="small">{k}: <code>{v}</code></div>)}
    </div>
  );
}

export default function Workspace() {
  const { id } = useParams();
  const toast = useToast();
  const [repo, setRepo] = useState(null);
  const [history, setHistory] = useState([]);
  const [task, setTask] = useState(null);
  const [request, setRequest] = useState('');
  const [tab, setTab] = useState('diff');
  const [rtab, setRtab] = useState('diff');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [gitKey, setGitKey] = useState(0);
  const taskId = useRef(null);

  const loadHistory = useCallback(async () => {
    try { setHistory((await api.get(`/repos/${id}/tasks`)).tasks); } catch { /* shown elsewhere */ }
  }, [id]);

  const loadTask = useCallback(async (tid) => {
    try { const t = (await api.get(`/tasks/${tid}`)).task; if (taskId.current === tid) setTask(t); return t; }
    catch (e) { toast(e.message, 'err'); }
  }, [toast]);

  useEffect(() => {
    api.get(`/repos/${id}`).then((r) => setRepo(r.repo)).catch((e) => toast(e.message, 'err'));
    loadHistory();
  }, [id]); // eslint-disable-line

  const select = (tid) => { taskId.current = tid; setTask(null); loadTask(tid); };

  // poll while the server is working
  useEffect(() => {
    if (!task || !BUSY[task.status]) return;
    const t = setInterval(async () => {
      const n = await loadTask(task.id);
      if (n && !BUSY[n.status]) { loadHistory(); setGitKey((k) => k + 1); }
    }, 2000);
    return () => clearInterval(t);
  }, [task?.id, task?.status]); // eslint-disable-line

  useEffect(() => {
    if (task?.apply_result) setMsg((m) => m || `RepoPilot: ${task.user_request} (${(task.changed_files || []).join(', ')})`.slice(0, 190));
  }, [task?.id, task?.apply_result]); // eslint-disable-line

  async function act(fn, ok) {
    setBusy(true);
    try { const out = await fn(); if (ok) toast(ok); return out; } catch (e) { toast(e.message, 'err'); }
    finally { setBusy(false); }
  }
  const call = (path, ok) => act(async () => { await api.post(path); await loadTask(task.id); loadHistory(); }, ok);

  async function start(e) {
    e.preventDefault();
    const out = await act(() => api.post(`/repos/${id}/tasks`, { user_request: request }));
    if (out) { setRequest(''); setMsg(''); select(out.id); loadHistory(); }
  }

  async function reindex() {
    const out = await act(() => api.post(`/repos/${id}/reindex`, { force: true }));
    if (out) toast(`Index refreshed — ${out.chunks} chunks.`);
  }

  if (!repo) return <div className="spinner" aria-label="Loading" />;

  const rv = task?.review_result;
  const change = rv?.proposed_changes?.[0];
  const ar = task?.apply_result;
  const rar = task?.repair_apply_result;
  const rep = task?.repair_result;
  const failing = task && ['applied', 'repaired', 'repair_failed'].includes(task.status) && task.validation_passed === false;
  const attemptsLeft = task ? task.max_repair_attempts - task.repair_attempts : 0;
  const idx = stageIndex(task);

  return (
    <div className="stack">
      <div className="row between">
        <div><Link to="/repos" className="muted small">← Repositories</Link><h2 style={{ marginTop: 6, wordBreak: 'break-all' }}>{repo.name}</h2>
          <span className="muted small">{repo.scan?.file_count ?? 0} files · {repo.chunk_count} code chunks</span></div>
        <button className="btn" onClick={reindex} disabled={busy}><RefreshCw size={15} /> Re-index</button>
      </div>

      <form className="glass pad stack" onSubmit={start}>
        <h3>What should RepoPilot do?</h3>
        <textarea value={request} onChange={(e) => setRequest(e.target.value)} placeholder="Example: Check index.js and fix the error on startup." required minLength={5} aria-label="Task" />
        <div><button className="btn primary" disabled={busy || BUSY[task?.status]}>Analyze and prepare change</button></div>
      </form>

      {task && (
        <div className="stages" aria-label="Progress">
          {['Analyze', 'Review', 'Apply and validate', 'Commit'].map((s, i) => <span key={s} className={`stage ${i < idx ? 'done' : i === idx ? 'now' : ''}`}>{s}</span>)}
        </div>
      )}

      {task && BUSY[task.status] && <div className="glass pad working"><div className="spinner" /><div>{BUSY[task.status]}<div className="muted small">This can take a minute. You can leave this page — progress is saved.</div></div></div>}

      {task?.status === 'no_change' && <div className="banner"><b>No change needed</b><span className="small">{rv?.change_result?.message || 'RepoPilot found nothing to change for this request.'}</span></div>}
      {task?.status === 'rejected' && <div className="banner warn"><b>Change rejected</b><span className="small">No file was modified.</span></div>}
      {task?.status === 'failed' && <div className="banner bad"><b>This task could not finish</b><span className="small">{task.error}</span></div>}

      {task?.status === 'review' && rv && (
        <div className="glass pad stack">
          <h3>Review proposed change</h3>
          {rv.security_warnings?.length > 0 && <div className="banner warn"><b>Security notes</b>{rv.security_warnings.map((w, i) => <div key={i} className="small">{w}</div>)}</div>}
          <div className="seg" role="tablist">
            {[['understanding', 'Understanding'], ['plan', 'Plan'], ['diff', 'Diff']].map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}
          </div>
          {tab === 'understanding' && <p style={{ whiteSpace: 'pre-wrap' }}>{rv.task_understanding}</p>}
          {tab === 'plan' && <ol>{(rv.plan || []).map((s, i) => <li key={i}>{s}</li>)}</ol>}
          {tab === 'diff' && (<>
            {change && <div className="small"><b>File:</b> <code>{change.file_path}</code>{change.reason && <> · {change.reason}</>}</div>}
            <Diff text={rv.diff} />
          </>)}
          <div className="row">
            <button className="btn primary" disabled={busy} onClick={() => call(`/tasks/${task.id}/approve`)}>Approve and apply</button>
            <button className="btn ghost" disabled={busy} onClick={() => call(`/tasks/${task.id}/reject`, 'Change rejected. No file was modified.')}>Reject</button>
          </div>
        </div>
      )}

      {ar && !['review', 'analyzing'].includes(task.status) && (
        <ResultBanner
          title={ar.change_result?.status !== 'modified' ? 'Change not applied' : ar.validation_result?.success ? 'Change applied — validation passed' : 'Change applied — validation failed'}
          ok={ar.change_result?.status !== 'modified' ? null : !!ar.validation_result?.success}
          rows={[['File', ar.change_result?.file_path], ['Backup', ar.change_result?.backup_path], ['Branch', ar.applied_on_branch]]} />
      )}
      {rar && (
        <ResultBanner
          title={rar.validation_result?.success ? 'Repair applied — validation passed' : 'Repair applied — still failing'}
          ok={!!rar.validation_result?.success}
          rows={[['File', rar.repair_result?.file_path], ['Backup', rar.repair_result?.backup_path], ['Attempt', `${task.repair_attempts} of ${task.max_repair_attempts}`]]} />
      )}
      {task?.status === 'repair_failed' && <div className="banner bad"><b>Repair not applied</b><span className="small">{task.error}</span></div>}

      {failing && (
        <details className="glass pad"><summary style={{ cursor: 'pointer' }}>Validation output</summary>
          <pre className="diff">{JSON.stringify((rar || ar).validation_result, null, 2)}</pre></details>
      )}

      {failing && (
        <div className="glass pad stack">
          <h3>Repair assistant</h3>
          {attemptsLeft > 0
            ? <><p className="muted">The change did not pass validation. RepoPilot can analyze the failure and propose a minimal repair for your review. Attempts left: {attemptsLeft}.</p>
                <div><button className="btn primary" disabled={busy} onClick={() => call(`/tasks/${task.id}/repair/prepare`)}>Analyze failure and prepare repair</button></div></>
            : <div className="banner bad">Maximum repair attempts reached. RepoPilot will not try again automatically — check the validation output and describe the problem in a new task.</div>}
        </div>
      )}

      {task?.status === 'repair_review' && rep && (
        <div className="glass pad stack">
          <h3>Review proposed repair</h3>
          <div className="seg" role="tablist">
            {[['analysis', 'Failure analysis'], ['diff', 'Repair diff']].map(([k, l]) => <button key={k} role="tab" aria-selected={rtab === k} className={rtab === k ? 'on' : ''} onClick={() => setRtab(k)}>{l}</button>)}
          </div>
          {rtab === 'analysis' && <p style={{ whiteSpace: 'pre-wrap' }}>{rep.failure_analysis}</p>}
          {rtab === 'diff' && (<>
            <div className="small"><b>File:</b> <code>{rep.repair_proposal?.file_path}</code> · {rep.repair_proposal?.reason}</div>
            <Diff text={rep.repair_diff} />
          </>)}
          <div className="row">
            <button className="btn primary" disabled={busy} onClick={() => call(`/tasks/${task.id}/repair/approve`)}>Approve repair</button>
            <button className="btn ghost" disabled={busy} onClick={() => call(`/tasks/${task.id}/reject`, 'Repair rejected. No additional file was modified.')}>Reject repair</button>
          </div>
        </div>
      )}

      {task?.validation_passed && ['applied', 'repaired'].includes(task.status) && (
        <div className="glass pad stack">
          {task.commit_hash
            ? <><h3>Committed</h3><p className="muted">Your change is committed on <code>{task.branch}</code>. Push it and open a pull request from the Git panel below.</p></>
            : <>
                <h3>Commit this change</h3>
                <label>Commit message<input value={msg} onChange={(e) => setMsg(e.target.value)} /></label>
                <div className="small muted">Only these files are committed: <code>{(task.changed_files || []).join(', ')}</code>. Backup files are never included.</div>
                <div><button className="btn primary" disabled={busy || msg.trim().length < 3}
                  onClick={() => act(async () => {
                    const out = await api.post(`/repos/${id}/git/commit`, { task_id: task.id, message: msg });
                    if (out.success === false) throw new Error(out.message || 'Commit failed.');
                    await loadTask(task.id); loadHistory(); setGitKey((k) => k + 1);
                  }, 'Committed.')}>Commit change</button></div>
              </>}
        </div>
      )}

      <GitPanel repoId={id} refreshKey={gitKey} task={task} />

      <div className="glass pad stack">
        <h3>Task history</h3>
        {history.length === 0 && <p className="muted">Tasks you run on this repository appear here.</p>}
        <div className="hist">
          {history.map((h) => (
            <button key={h.id} className={task?.id === h.id ? 'on' : ''} onClick={() => select(h.id)}>
              <span className="t">{h.user_request}</span>
              <span className="muted small">{h.status.replace('_', ' ')} · {new Date(h.created_at).toLocaleString()}{h.commit_hash ? ' · committed' : ''}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
