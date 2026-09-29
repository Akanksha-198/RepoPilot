import { createContext, useContext, useState, useCallback } from 'react';

const Ctx = createContext(() => {});
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const push = useCallback((message, kind = 'ok') => {
    const id = Math.random().toString(36).slice(2);
    setItems((s) => [...s, { id, message, kind }]);
    setTimeout(() => setItems((s) => s.filter((i) => i.id !== id)), 5000);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((i) => <div key={i.id} className={`toast ${i.kind}`}>{i.message}</div>)}
      </div>
    </Ctx.Provider>
  );
}
