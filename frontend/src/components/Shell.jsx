import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { FolderGit2, Settings, ShieldCheck, LogOut } from 'lucide-react';
import { useAuth } from '../auth.jsx';

const LEVELS = ['', 'Read', 'Analyze', 'Write', 'Commit', 'Push', 'Pull request'];

export default function Shell() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <div className="shell">
      <aside className="side glass">
        <div className="brand">RepoPilot</div>
        <nav>
          <NavLink to="/repos"><FolderGit2 size={18} /> Repositories</NavLink>
          <NavLink to="/settings"><Settings size={18} /> Settings</NavLink>
          {user.role === 'admin' && <NavLink to="/admin"><ShieldCheck size={18} /> Admin</NavLink>}
        </nav>
        <div className="grow" />
        <div className="me">
          <div className="me-name">{user.name}</div>
          <div className="muted small">{user.email}</div>
          <div className="chip">{LEVELS[user.permission_level]} access</div>
          <button className="btn ghost full" onClick={async () => { await logout(); nav('/login'); }}>
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>
      <main className="main"><Outlet /></main>
    </div>
  );
}
