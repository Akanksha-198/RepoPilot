import jwt from 'jsonwebtoken';
import { cfg } from './config.js';
import { q } from './db.js';
import { audit } from './audit.js';

export const LEVELS = { READ: 1, ANALYZE: 2, WRITE: 3, COMMIT: 4, PUSH: 5, PR: 6 };

export const wrap = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

export const requireAuth = wrap(async (req, res, next) => {
  const token = req.cookies?.rp_token;
  if (!token) return res.status(401).json({ error: 'Please sign in.' });
  let payload;
  try { payload = jwt.verify(token, cfg.jwtSecret); }
  catch { return res.status(401).json({ error: 'Your session expired. Please sign in again.' }); }
  const { rows } = await q(
    `select id,email,name,role,permission_level,(github_token_enc is not null) as has_github_token from users where id=$1`,
    [payload.sub]);
  if (!rows[0]) return res.status(401).json({ error: 'Account not found.' });
  req.user = rows[0];
  next();
});

export const requireLevel = (name) => (req, res, next) => {
  if (req.user.permission_level >= LEVELS[name]) return next();
  audit(req, 'permission.denied', name);
  res.status(403).json({ error: `This action needs ${name} permission (level ${LEVELS[name]}). Yours is level ${req.user.permission_level}. Ask an admin to raise it.` });
};

export const requireAdmin = (req, res, next) =>
  req.user.role === 'admin' ? next() : res.status(403).json({ error: 'Admins only.' });

// CSRF defence: cookies alone are never enough - a custom header forces a CORS preflight.
export const csrfGuard = (req, res, next) => {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) return next();
  if (req.get('x-requested-with') !== 'RepoPilot') return res.status(403).json({ error: 'Blocked by CSRF protection.' });
  next();
};

export function errorHandler(err, req, res, _next) {
  if (err.name === 'ZodError') {
    return res.status(400).json({ error: err.issues.map((i) => `${i.path.join('.') || 'input'}: ${i.message}`).join('; ') });
  }
  console.error(JSON.stringify({ level: 'error', path: req.path, msg: err.message }));
  res.status(err.status || 500).json({ error: err.status ? err.message : 'Something went wrong on our side. Please try again.' });
}
