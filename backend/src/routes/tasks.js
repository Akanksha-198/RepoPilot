import { Router } from 'express';
import { z } from 'zod';
import { q } from '../db.js';
import { ai } from '../ai.js';
import { cfg } from '../config.js';
import { audit } from '../audit.js';
import { wrap, requireLevel } from '../middleware.js';
import { ownedRepo } from './repos.js';

const r = Router();
const BUSY = ['analyzing', 'applying', 'repairing', 'repair_applying'];
const bg = (fn) => setImmediate(() => fn().catch((e) => console.error('bg error', e.message)));

async function setTask(id, fields) {
  const keys = Object.keys(fields);
  const vals = keys.map((k) => {
    const v = fields[k];
    return v !== null && typeof v === 'object' ? JSON.stringify(v) : v;
  });
  await q(`update tasks set ${keys.map((k, i) => `${k}=$${i + 2}`).join(',')}, updated_at=now() where id=$1`, [id, ...vals]);
}
const fail = (id, e, status = 'failed') => setTask(id, { status, error: String(e.message || e).slice(0, 600) });

async function ownedTask(req) {
  const { rows } = await q('select * from tasks where id=$1 and user_id=$2', [req.params.id, req.user.id]);
  if (!rows[0]) { const e = new Error('Task not found.'); e.status = 404; throw e; }
  return rows[0];
}
const latest = (t) => t.repair_apply_result || t.apply_result;
const validationOf = (t) => latest(t)?.validation_result;

function view(t) {
  const v = validationOf(t);
  return { ...t, validation_passed: v ? !!v.success : null, max_repair_attempts: cfg.maxRepairAttempts };
}

r.get('/repos/:repoId/tasks', wrap(async (req, res) => {
  const repo = await ownedRepo(req, req.params.repoId);
  const { rows } = await q(
    'select id,user_request,status,branch,commit_hash,created_at from tasks where repo_id=$1 order by id desc limit 50', [repo.id]);
  res.json({ tasks: rows });
}));

r.post('/repos/:repoId/tasks', requireLevel('ANALYZE'), wrap(async (req, res) => {
  const repo = await ownedRepo(req, req.params.repoId);
  if (repo.status !== 'ready') return res.status(409).json({ error: 'Repository is not ready yet.' });
  const { user_request } = z.object({ user_request: z.string().trim().min(5, 'Describe the task in a sentence.').max(2000) }).parse(req.body);
  const busy = await q('select 1 from tasks where repo_id=$1 and status = any($2) limit 1', [repo.id, BUSY]);
  if (busy.rowCount) return res.status(409).json({ error: 'Another task is still running on this repository.' });

  const t = (await q('insert into tasks(user_id,repo_id,user_request) values ($1,$2,$3) returning id', [req.user.id, repo.id, user_request])).rows[0];
  audit(req, 'task.create', String(t.id), { repo: repo.name });
  res.status(202).json({ id: t.id });

  bg(async () => {
    try {
      const out = await ai.analyze({ user_request, repository_path: repo.path, repository_name: repo.key });
      if (out.diff) return setTask(t.id, { status: 'review', review_result: out });
      const cr = out.change_result || {};
      if (cr.status === 'no_change_needed') return setTask(t.id, { status: 'no_change', review_result: out });
      return setTask(t.id, { status: 'failed', review_result: out, error: cr.message || 'No diff was generated.' });
    } catch (e) { await fail(t.id, e); }
  });
}));

r.get('/tasks/:id', wrap(async (req, res) => res.json({ task: view(await ownedTask(req)) })));

r.post('/tasks/:id/approve', requireLevel('WRITE'), wrap(async (req, res) => {
  const t = await ownedTask(req);
  if (t.status !== 'review') return res.status(409).json({ error: 'This task is not waiting for review.' });
  await setTask(t.id, { status: 'applying', error: null });
  audit(req, 'task.approve', String(t.id), { file: t.review_result?.proposed_changes?.[0]?.file_path });
  res.status(202).json({ id: t.id });

  bg(async () => {
    try {
      const out = await ai.apply(t.review_result);
      const cr = out.change_result || {};
      if (cr.status === 'modified') {
        await setTask(t.id, { status: 'applied', apply_result: out, branch: out.applied_on_branch, changed_files: [cr.file_path] });
      } else {
        await setTask(t.id, { status: 'failed', apply_result: out, error: cr.message || 'The change was not applied.' });
      }
    } catch (e) { await fail(t.id, e); }
  });
}));

r.post('/tasks/:id/reject', wrap(async (req, res) => {
  const t = await ownedTask(req);
  if (!['review', 'repair_review'].includes(t.status)) return res.status(409).json({ error: 'Nothing to reject.' });
  if (t.status === 'review') await setTask(t.id, { status: 'rejected' });
  else await setTask(t.id, { status: t.repair_apply_result ? 'repaired' : 'applied', repair_result: null });
  audit(req, 'task.reject', String(t.id), { stage: t.status });
  res.json({ ok: true });
}));

// ---------------------------------------------------------------- repair (Phase 5)
r.post('/tasks/:id/repair/prepare', requireLevel('WRITE'), wrap(async (req, res) => {
  const t = await ownedTask(req);
  const v = validationOf(t);
  if (!['applied', 'repaired', 'repair_failed'].includes(t.status) || !v || v.success)
    return res.status(409).json({ error: 'There is no failed validation to repair.' });
  if (t.repair_attempts >= cfg.maxRepairAttempts)
    return res.status(409).json({ error: `Maximum repair attempts (${cfg.maxRepairAttempts}) reached. Review the failure manually.` });
  await setTask(t.id, { status: 'repairing', error: null });
  audit(req, 'task.repair_prepare', String(t.id));
  res.status(202).json({ id: t.id });

  bg(async () => {
    try {
      const out = await ai.repairPrepare(latest(t));
      if (out.repair_result?.status === 'ready_for_review') await setTask(t.id, { status: 'repair_review', repair_result: out });
      else await fail(t.id, new Error(out.repair_result?.message || 'Repair could not be prepared.'), 'repair_failed');
    } catch (e) { await fail(t.id, e, 'repair_failed'); }
  });
}));

r.post('/tasks/:id/repair/approve', requireLevel('WRITE'), wrap(async (req, res) => {
  const t = await ownedTask(req);
  if (t.status !== 'repair_review') return res.status(409).json({ error: 'No repair is waiting for review.' });
  await setTask(t.id, { status: 'repair_applying', error: null });
  audit(req, 'task.repair_approve', String(t.id), { file: t.repair_result?.repair_proposal?.file_path });
  res.status(202).json({ id: t.id });

  bg(async () => {
    try {
      const out = await ai.repairApply(t.apply_result, t.repair_result);
      const rr = out.repair_result || {};
      if (rr.status === 'modified') {
        const files = [...new Set([...(t.changed_files || []), rr.file_path])];
        await setTask(t.id, { status: 'repaired', repair_apply_result: out, repair_attempts: t.repair_attempts + 1, changed_files: files, repair_result: null });
      } else {
        // includes stale-file rejection: the file changed after the proposal was made
        await fail(t.id, new Error(rr.message || 'The repair was not applied.'), 'repair_failed');
      }
    } catch (e) { await fail(t.id, e, 'repair_failed'); }
  });
}));

export default r;
