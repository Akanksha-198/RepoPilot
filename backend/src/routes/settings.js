import { Router } from 'express';
import { z } from 'zod';
import { q } from '../db.js';
import { encrypt } from '../crypto.js';
import { audit } from '../audit.js';
import { wrap } from '../middleware.js';

const r = Router();

r.put('/github-token', wrap(async (req, res) => {
  const { token } = z.object({ token: z.string().trim().min(20).max(255) }).parse(req.body);
  await q('update users set github_token_enc=$2 where id=$1', [req.user.id, encrypt(token)]);
  audit(req, 'settings.github_token_set');
  res.json({ ok: true });
}));

r.delete('/github-token', wrap(async (req, res) => {
  await q('update users set github_token_enc=null where id=$1', [req.user.id]);
  audit(req, 'settings.github_token_removed');
  res.json({ ok: true });
}));

export default r;
