import { Router } from 'express';
import { z } from 'zod';
import { q } from '../db.js';
import { ai } from '../ai.js';
import { audit } from '../audit.js';
import { decrypt } from '../crypto.js';
import { wrap, requireLevel } from '../middleware.js';

const r = Router();
const GITHUB = /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+?(\.git)?\/?$/;
const bg = (fn) => setImmediate(() => fn().catch((e) => console.error('bg error', e.message)));

export async function userToken(userId) {
  const { rows } = await q('select github_token_enc from users where id=$1', [userId]);
  return rows[0]?.github_token_enc ? decrypt(rows[0].github_token_enc) : '';
}

export async function ownedRepo(req, id = req.params.id) {
  const { rows } = await q('select * from repos where id=$1 and user_id=$2', [id, req.user.id]);
  if (!rows[0]) { const e = new Error('Repository not found.'); e.status = 404; throw e; }
  return rows[0];
}

const clean = ({ path, ...rest }) => rest; // never expose server paths to the browser

r.get('/', wrap(async (req, res) => {
  const { rows } = await q('select * from repos where user_id=$1 order by id desc', [req.user.id]);
  res.json({ repos: rows.map(clean) });
}));

r.get('/:id', wrap(async (req, res) => res.json({ repo: clean(await ownedRepo(req)) })));

r.post('/', requireLevel('ANALYZE'), wrap(async (req, res) => {
  const { github_url } = z.object({ github_url: z.string().trim().regex(GITHUB, 'Use a URL like https://github.com/owner/repo') }).parse(req.body);
  const url = github_url.replace(/\.git$/, '').replace(/\/$/, '');
  const name = url.split('/').slice(-2).join('/');
  const slug = name.replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 60);
  const key = `u${req.user.id}_${slug}`;
  let repo;
  try {
    repo = (await q('insert into repos(user_id,url,name,key) values ($1,$2,$3,$4) returning *', [req.user.id, url, name, key])).rows[0];
  } catch (e) {
    if (e.code === '23505') return res.status(409).json({ error: 'You have already added this repository.' });
    throw e;
  }
  audit(req, 'repo.clone', url);
  res.status(202).json({ repo: clean(repo) });

  bg(async () => {
    try {
      const token = await userToken(req.user.id);
      const out = await ai.clone({ github_url: url + '.git', owner_key: `u${req.user.id}`, repository_key: key }, token);
      await q(`update repos set status='ready', path=$2, chunk_count=$3, scan=$4, error=null where id=$1`,
        [repo.id, out.repository_path, out.chunks, JSON.stringify(out.scan)]);
    } catch (e) {
      await q(`update repos set status='failed', error=$2 where id=$1`, [repo.id, e.message.slice(0, 500)]);
    }
  });
}));

r.post('/:id/reindex', requireLevel('ANALYZE'), wrap(async (req, res) => {
  const repo = await ownedRepo(req);
  if (repo.status !== 'ready') return res.status(409).json({ error: 'Repository is not ready.' });
  const force = req.body?.force === true;
  const out = await ai.reindex({ repository_path: repo.path, repository_name: repo.key, force });
  await q('update repos set chunk_count=$2, scan=$3 where id=$1', [repo.id, out.chunks, JSON.stringify(out.scan)]);
  audit(req, 'repo.reindex', repo.name, { status: out.status, changed: out.changed });
  res.json({ status: out.status, chunks: out.chunks, changed: out.changed });
}));

r.delete('/:id', requireLevel('WRITE'), wrap(async (req, res) => {
  const repo = await ownedRepo(req);
  if (repo.path) await ai.deleteRepo({ repository_path: repo.path, repository_name: repo.key }).catch(() => {});
  await q('delete from repos where id=$1', [repo.id]);
  audit(req, 'repo.delete', repo.name);
  res.json({ ok: true });
}));

export default r;
