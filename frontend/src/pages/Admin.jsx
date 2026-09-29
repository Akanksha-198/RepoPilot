import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { useToast } from '../components/Toast.jsx';

const LEVELS = [['1', 'Read'], ['2', 'Analyze'], ['3', 'Write'], ['4', 'Commit'], ['5', 'Push'], ['6', 'Pull request']];

export default function Admin() {
  const toast = useToast();
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);

  const load = async () => {
    try {
      setUsers((await api.get('/admin/users')).users);
      setLogs((await api.get('/admin/audit')).logs);
    } catch (e) { toast(e.message, 'err'); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line

  async function setLevel(u, level) {
    try { await api.patch(`/admin/users/${u.id}`, { permission_level: Number(level) }); toast('Access updated.'); load(); }
    catch (e) { toast(e.message, 'err'); }
  }

  return (
    <div className="stack">
      <h2>Admin</h2>
      <div className="glass pad stack">
        <h3>People and access</h3>
        <p className="muted">Access is cumulative: each level includes everything below it.</p>
        <div className="tablewrap"><table>
          <thead><tr><th>Name</th><th>Email</th><th>Access</th></tr></thead>
          <tbody>{users.map((u) => (
            <tr key={u.id}><td>{u.name} {u.role === 'admin' && <span className="chip">admin</span>}</td><td>{u.email}</td>
              <td><select value={u.permission_level} onChange={(e) => setLevel(u, e.target.value)} aria-label={`Access for ${u.name}`}>
                {LEVELS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}</select></td></tr>))}
          </tbody></table></div>
      </div>
      <div className="glass pad stack">
        <h3>Audit trail</h3>
        <div className="tablewrap"><table>
          <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Target</th></tr></thead>
          <tbody>{logs.map((l) => (
            <tr key={l.id}><td className="small">{new Date(l.created_at).toLocaleString()}</td><td>{l.email || '—'}</td><td>{l.action}</td><td className="small">{l.target}</td></tr>))}
          </tbody></table></div>
      </div>
    </div>
  );
}
