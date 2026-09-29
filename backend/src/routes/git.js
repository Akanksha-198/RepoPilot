import { Router } from 'express';
import { z } from 'zod';
import { q } from '../db.js';
import { ai } from '../ai.js';
import { audit } from '../audit.js';
import { wrap, requireLevel } from '../middleware.js';
import { ownedRepo, userToken } from './repos.js';

const r = Router({ mergeParams: true });
const path = async (req) => (await ownedRepo(req, req.params.repoId)).path;
const need = (repo) => { if (!repo.path) { const e = new Error('Repository is not ready.'); e.status = 409; throw e; } };

r.get('/status', requireLevel('READ'), wrap(async (req, res) => {
  const repo = await ownedRepo(req, req.params.repoId); need(repo);
  res.json(await ai.git('status', { repository_path: repo.path }));
}));

r.get('/last-commit', requireLevel('READ'), wrap(async (req, res) => {
  const repo = await ownedRepo(req, req.params.repoId); need(repo);
  res.json(await ai.git('last-commit', { repository_path: repo.path }));
}));

r.get('/diff', requireLevel('READ'), wrap(async (req, res) => {
  const repo = await ownedRepo(req, req.params.repoId); need(repo);
  res.json(await ai.git('diff', { repository_path: repo.path }));
}));

// Commit: only the files RepoPilot changed for this task, and only after validation passed.
r.post('/commit', requireLevel('COMMIT'), wrap(async (req, res) => {
  const repo = await ownedRepo(req, req.params.repoId); need(repo);
  const b = z.object({ task_id: z.number().int(), message: z.string().trim().min(3).max(200) }).parse(req.body);
  const { rows } = await q('select * from tasks where id=$1 and repo_id=$2 and user_id=$3', [b.task_id, repo.id, req.user.id]);
  const t = rows[0];
  if (!t) return res.status(404).json({ error: 'Task not found.' });
  const v = (t.repair_apply_result || t.apply_result)?.validation_result;
  if (!['applied', 'repaired'].includes(t.status) || !v?.success)
    return res.status(409).json({ error: 'Only changes that passed validation can be committed.' });
  if (t.commit_hash) return res.status(409).json({ error: 'This task is already committed.' });
  const out = await ai.git('commit', { repository_path: repo.path, files: t.changed_files, message: b.message });
  if (out.success) await q('update tasks set commit_hash=$2, updated_at=now() where id=$1', [t.id, out.commit_hash || 'committed']);
  audit(req, 'git.commit', repo.name, { task: t.id, files: t.changed_files, ok: out.success });
  res.json(out);
}));

const simple = (route, action, level, auditName, withToken = false) =>
  r.post(route, requireLevel(level), wrap(async (req, res) => {
    const repo = await ownedRepo(req, req.params.repoId); need(repo);
    const token = withToken ? await userToken(req.user.id) : '';
    if (withToken && !token) return res.status(400).json({ error: 'Add your GitHub token in Settings first.' });
    const out = await ai.git(action, { repository_path: repo.path }, token);
    audit(req, auditName, repo.name, { ok: out.success });
    res.json(out);
  }));

simple('/push', 'push', 'PUSH', 'git.push', true);
simple('/undo', 'undo', 'COMMIT', 'git.undo');
simple('/revert', 'revert', 'COMMIT', 'git.revert');
simple('/ignore-backups', 'ignore-backups', 'WRITE', 'git.ignore_backups');

r.post('/pr', requireLevel('PR'), wrap(async (req, res) => {
  const repo = await ownedRepo(req, req.params.repoId); need(repo);
  const b = z.object({ title: z.string().trim().min(3).max(200), body: z.string().max(5000).default('') }).parse(req.body);
  const token = await userToken(req.user.id);
  if (!token) return res.status(400).json({ error: 'Add your GitHub token in Settings first.' });
  const out = await ai.git('pr', { repository_path: repo.path, title: b.title, body: b.body }, token);
  audit(req, 'git.pr', repo.name, { ok: out.success, url: out.url });
  res.json(out);
}));

export default r;
