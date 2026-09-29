import { cfg } from './config.js';

async function call(path, body, { token, timeoutMs = 15 * 60 * 1000 } = {}) {
  let res;
  try {
    res = await fetch(cfg.aiUrl + path, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-internal-key': cfg.aiKey,
        ...(token ? { 'x-github-token': token } : {}),
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    throw new Error(e.name === 'TimeoutError' ? 'The AI service timed out.' : 'The AI service is unreachable.');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `AI service error (${res.status})`);
  return data;
}

export const ai = {
  clone: (b, token) => call('/repos/clone', b, { token }),
  reindex: (b) => call('/repos/reindex', b),
  deleteRepo: (b) => call('/repos/delete', b),
  analyze: (b) => call('/tasks/analyze', b),
  apply: (state) => call('/tasks/apply', { state }),
  repairPrepare: (state) => call('/tasks/repair/prepare', { state }),
  repairApply: (apply_state, repair_result) => call('/tasks/repair/apply', { apply_state, repair_result }),
  git: (action, b, token) => call(`/git/${action}`, b, { token, timeoutMs: 120000 }),
};
