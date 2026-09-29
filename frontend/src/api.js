const BASE = import.meta.env.VITE_API_URL || '';

async function req(method, path, body) {
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'RepoPilot' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('rp-unauth'));
    const err = new Error(data?.error || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  get: (p) => req('GET', p),
  post: (p, b = {}) => req('POST', p, b),
  put: (p, b = {}) => req('PUT', p, b),
  patch: (p, b = {}) => req('PATCH', p, b),
  del: (p) => req('DELETE', p),
};
