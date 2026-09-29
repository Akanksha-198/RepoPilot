import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import cookieParser from 'cookie-parser';
import rateLimit from 'express-rate-limit';
import { cfg } from './config.js';
import { initDb, q } from './db.js';
import { requireAuth, requireAdmin, csrfGuard, errorHandler } from './middleware.js';
import auth from './routes/auth.js';
import repos from './routes/repos.js';
import tasks from './routes/tasks.js';
import git from './routes/git.js';
import settings from './routes/settings.js';
import admin from './routes/admin.js';

const app = express();
app.set('trust proxy', 1);
app.use(helmet());
app.use(cors({ origin: cfg.corsOrigins, credentials: true }));
app.use(express.json({ limit: '200kb' }));
app.use(cookieParser());
app.use(rateLimit({ windowMs: 60 * 1000, limit: 240, standardHeaders: true, legacyHeaders: false }));

app.get('/api/health', async (req, res) => {
  try { await q('select 1'); res.json({ ok: true }); } catch { res.status(503).json({ ok: false }); }
});

app.use('/api', csrfGuard);
app.use('/api/auth', auth);
app.use('/api/repos', requireAuth, repos);
app.use('/api/repos/:repoId/git', requireAuth, git);
app.use('/api', requireAuth, tasks);
app.use('/api/settings', requireAuth, settings);
app.use('/api/admin', requireAuth, requireAdmin, admin);

app.use('/api', (req, res) => res.status(404).json({ error: 'Not found.' }));
app.use(errorHandler);

await initDb();
app.listen(cfg.port, () => console.log(`RepoPilot API listening on :${cfg.port}`));
