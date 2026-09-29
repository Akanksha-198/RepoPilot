import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth.jsx';
import Shell from './components/Shell.jsx';
import Auth from './pages/Auth.jsx';
import Repos from './pages/Repos.jsx';
import Workspace from './pages/Workspace.jsx';
import Settings from './pages/Settings.jsx';
import Admin from './pages/Admin.jsx';

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <div className="center-screen"><div className="spinner" aria-label="Loading" /></div>;
  return (
    <>
      <div className="orb o1" /><div className="orb o2" />
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/repos" replace /> : <Auth />} />
        <Route element={user ? <Shell /> : <Navigate to="/login" replace />}>
          <Route path="/repos" element={<Repos />} />
          <Route path="/repos/:id" element={<Workspace />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={user?.role === 'admin' ? <Admin /> : <Navigate to="/repos" replace />} />
        </Route>
        <Route path="*" element={<Navigate to={user ? '/repos' : '/login'} replace />} />
      </Routes>
    </>
  );
}
