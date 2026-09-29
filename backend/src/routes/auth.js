import { Router } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import rateLimit from 'express-rate-limit';
import { z } from 'zod';
import { cfg } from '../config.js';
import { q } from '../db.js';
import { audit } from '../audit.js';
import { wrap, requireAuth } from '../middleware.js';

const r = Router();
const limiter = rateLimit({ windowMs: 15 * 60 * 1000, limit: 20, standardHeaders: true, legacyHeaders: false,
  message: { error: 'Too many attempts. Try again in a few minutes.' } });

const cookieOpts = { httpOnly: true, secure: cfg.cookieSecure, sameSite: 'lax', maxAge: 7 * 24 * 3600 * 1000, path: '/' };
const publicUser = (u) => ({ id: u.id, email: u.email, name: u.name, role: u.role,
  permission_level: u.permission_level, has_github_token: !!u.has_github_token });
const sign = (id) => jwt.sign({ sub: id }, cfg.jwtSecret, { expiresIn: '7d' });

r.post('/register', limiter, wrap(async (req, res) => {
  const b = z.object({
    name: z.string().trim().min(2).max(60),
    email: z.string().trim().toLowerCase().email().max(120),
    password: z.string().min(8, 'Use at least 8 characters').max(100),
  }).parse(req.body);
  const hash = await bcrypt.hash(b.password, 12);
  const first = (await q('select count(*)::int as n from users')).rows[0].n === 0;
  try {
    const { rows } = await q(
      `insert into users(email,name,password_hash,role,permission_level) values ($1,$2,$3,$4,$5)
       returning id,email,name,role,permission_level`,
      [b.email, b.name, hash, first ? 'admin' : 'user', first ? 6 : cfg.defaultLevel]);
    req.user = rows[0];
    audit(req, 'auth.register', b.email);
    res.cookie('rp_token', sign(rows[0].id), cookieOpts).status(201).json({ user: publicUser(rows[0]) });
  } catch (e) {
    if (e.code === '23505') return res.status(409).json({ error: 'An account with this email already exists.' });
    throw e;
  }
}));

r.post('/login', limiter, wrap(async (req, res) => {
  const b = z.object({ email: z.string().trim().toLowerCase().email(), password: z.string().min(1) }).parse(req.body);
  const { rows } = await q(`select *, (github_token_enc is not null) as has_github_token from users where email=$1`, [b.email]);
  const u = rows[0];
  const ok = u && (await bcrypt.compare(b.password, u.password_hash));
  if (!ok) { audit(req, 'auth.login_failed', b.email); return res.status(401).json({ error: 'Email or password is incorrect.' }); }
  req.user = u;
  audit(req, 'auth.login', b.email);
  res.cookie('rp_token', sign(u.id), cookieOpts).json({ user: publicUser(u) });
}));

r.post('/logout', (req, res) => res.clearCookie('rp_token', { path: '/' }).json({ ok: true }));
r.get('/me', requireAuth, (req, res) => res.json({ user: publicUser(req.user) }));

export default r;
