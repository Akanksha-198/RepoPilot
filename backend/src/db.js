import pg from 'pg';
import { cfg } from './config.js';

export const pool = new pg.Pool({ connectionString: cfg.databaseUrl, max: 10 });
export const q = (text, params) => pool.query(text, params);

const SCHEMA = `
create table if not exists users (
  id serial primary key,
  email text unique not null,
  name text not null,
  password_hash text not null,
  role text not null default 'user',
  permission_level int not null default 3,
  github_token_enc text,
  created_at timestamptz not null default now()
);
create table if not exists repos (
  id serial primary key,
  user_id int not null references users(id) on delete cascade,
  url text not null,
  name text not null,
  key text not null,
  path text,
  status text not null default 'cloning',
  error text,
  chunk_count int default 0,
  scan jsonb,
  created_at timestamptz not null default now(),
  unique (user_id, url)
);
create table if not exists tasks (
  id serial primary key,
  user_id int not null references users(id) on delete cascade,
  repo_id int not null references repos(id) on delete cascade,
  user_request text not null,
  status text not null default 'analyzing',
  error text,
  branch text,
  review_result jsonb,
  apply_result jsonb,
  repair_result jsonb,
  repair_apply_result jsonb,
  repair_attempts int not null default 0,
  changed_files jsonb not null default '[]',
  commit_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists audit_logs (
  id bigserial primary key,
  user_id int,
  action text not null,
  target text,
  meta jsonb,
  ip text,
  created_at timestamptz not null default now()
);
create index if not exists idx_tasks_repo on tasks(repo_id);
create index if not exists idx_audit_created on audit_logs(created_at desc);
`;

export async function initDb() {
  for (let i = 1; i <= 15; i++) {
    try {
      await pool.query(SCHEMA);
      // Anything left mid-flight by a restart can never finish - mark it failed.
      await pool.query(`update tasks set status='failed', error='Interrupted by a server restart. Please retry.'
                        where status in ('analyzing','applying','repairing','repair_applying')`);
      await pool.query(`update repos set status='failed', error='Interrupted by a server restart.' where status='cloning'`);
      return;
    } catch (e) {
      console.error(`Database not ready (${i}/15): ${e.message}`);
      await new Promise((r) => setTimeout(r, 2000));
    }
  }
  throw new Error('Could not connect to the database');
}
