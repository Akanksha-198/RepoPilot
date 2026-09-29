import { Router } from 'express';
import { z } from 'zod';
import { q } from '../db.js';
import { audit } from '../audit.js';
import { wrap } from '../middleware.js';

const r = Router();

r.get('/users', wrap(async (req, res) => {
  const { rows } = await q('select id,email,name,role,permission_level,created_at from users order by id');
  res.json({ users: rows });
}));

r.patch('/users/:id', wrap(async (req, res) => {
  const b = z.object({ permission_level: z.number().int().min(1).max(6), role: z.enum(['user', 'admin']).optional() }).parse(req.body);
  const id = Number(req.params.id);
  if (id === req.user.id) return res.status(400).json({ error: 'You cannot change your own access.' });
  await q('update users set permission_level=$2, role=coalesce($3, role) where id=$1', [id, b.permission_level, b.role ?? null]);
  audit(req, 'admin.user_updated', String(id), b);
  res.json({ ok: true });
}));

r.get('/audit', wrap(async (req, res) => {
  const { rows } = await q(
    `select a.id,a.action,a.target,a.meta,a.ip,a.created_at,u.email from audit_logs a
     left join users u on u.id=a.user_id order by a.id desc limit 200`);
  res.json({ logs: rows });
}));

export default r;
