import { useState } from 'react';
import { useAuth } from '../auth.jsx';

export default function Auth() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login');
  const [f, setF] = useState({ name: '', email: '', password: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault(); setErr(''); setBusy(true);
    try { await (mode === 'login' ? login({ email: f.email, password: f.password }) : register(f)); }
    catch (x) { setErr(x.message); }
    setBusy(false);
  }

  return (
    <div className="auth">
      <section>
        <h1>Review every change before it ships.</h1>
        <p className="lede">RepoPilot reads your GitHub repository, proposes the smallest fix, and waits for your approval before it touches a single file.</p>
      </section>
      <form className="glass pad stack" onSubmit={submit}>
        <div className="tabs" role="tablist">
          <button type="button" role="tab" aria-selected={mode === 'login'} className={mode === 'login' ? 'on' : ''} onClick={() => setMode('login')}>Sign in</button>
          <button type="button" role="tab" aria-selected={mode === 'register'} className={mode === 'register' ? 'on' : ''} onClick={() => setMode('register')}>Create account</button>
        </div>
        {mode === 'register' && <label>Name<input value={f.name} onChange={set('name')} autoComplete="name" required minLength={2} /></label>}
        <label>Email<input type="email" value={f.email} onChange={set('email')} autoComplete="email" required /></label>
        <label>Password<input type="password" value={f.password} onChange={set('password')} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'register' ? 8 : 1} /></label>
        {err && <div className="banner bad" role="alert">{err}</div>}
        <button className="btn primary full" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
      </form>
    </div>
  );
}
