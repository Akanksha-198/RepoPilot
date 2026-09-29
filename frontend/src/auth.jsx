import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api } from './api.js';

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try { setUser((await api.get('/auth/me')).user); } catch { setUser(null); }
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const onUnauth = () => setUser(null);
    window.addEventListener('rp-unauth', onUnauth);
    return () => window.removeEventListener('rp-unauth', onUnauth);
  }, [refresh]);

  const login = async (b) => setUser((await api.post('/auth/login', b)).user);
  const register = async (b) => setUser((await api.post('/auth/register', b)).user);
  const logout = async () => { await api.post('/auth/logout'); setUser(null); };

  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>;
}
