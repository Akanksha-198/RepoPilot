import 'dotenv/config';

const env = process.env;
const prod = env.NODE_ENV === 'production';

export const cfg = {
  prod,
  port: Number(env.PORT || 4000),
  databaseUrl: env.DATABASE_URL,
  jwtSecret: env.JWT_SECRET,
  encryptionKey: env.ENCRYPTION_KEY,          // 64 hex chars (32 bytes)
  aiUrl: env.AI_SERVICE_URL || 'http://ai:8000',
  aiKey: env.INTERNAL_API_KEY,
  corsOrigins: (env.CORS_ORIGINS || 'http://localhost:5173').split(',').map((s) => s.trim()),
  cookieSecure: env.COOKIE_SECURE ? env.COOKIE_SECURE === 'true' : prod,
  defaultLevel: Number(env.DEFAULT_PERMISSION_LEVEL || 3),
  maxRepairAttempts: Number(env.MAX_REPAIR_ATTEMPTS || 3),
};

const problems = [];
if (!cfg.databaseUrl) problems.push('DATABASE_URL is missing');
if (!cfg.jwtSecret || cfg.jwtSecret.length < 32) problems.push('JWT_SECRET must be at least 32 characters');
if (!/^[0-9a-f]{64}$/i.test(cfg.encryptionKey || '')) problems.push('ENCRYPTION_KEY must be 64 hex characters');
if (!cfg.aiKey || cfg.aiKey.length < 16) problems.push('INTERNAL_API_KEY must be at least 16 characters');
if (problems.length) {
  console.error('Configuration error:\n - ' + problems.join('\n - '));
  process.exit(1);
}
