import { q } from './db.js';

export function audit(req, action, target = null, meta = {}) {
  q('insert into audit_logs(user_id, action, target, meta, ip) values ($1,$2,$3,$4,$5)', [
    req.user?.id ?? null, action, target, JSON.stringify(meta), req.ip,
  ]).catch((e) => console.error('audit failed', e.message));
}
