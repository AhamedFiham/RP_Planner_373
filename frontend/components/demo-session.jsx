'use client';

import { createContext, useContext, useEffect, useState } from 'react';

const DemoSessionContext = createContext(null);
const sessionKey = 'rp-planner-demo-session';

export function DemoSessionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(sessionKey);
      const saved = stored ? JSON.parse(stored) : null;
      if (saved && typeof saved.email === 'string' && saved.email.trim()) {
        setUser({ email: saved.email });
      }
    } catch {
      // A missing, invalid or unavailable browser session means signed out.
    }
    setReady(true);
  }, []);

  function login(email) {
    const nextUser = { email };
    // Demo navigation only: no password or patient data is stored.
    sessionStorage.setItem(sessionKey, JSON.stringify(nextUser));
    setUser(nextUser);
  }

  function logout() {
    try {
      sessionStorage.removeItem(sessionKey);
    } catch {
      // Still clear the in-memory demo session if browser storage is unavailable.
    }
    setUser(null);
  }

  return (
    <DemoSessionContext.Provider value={{ user, ready, login, logout }}>
      {children}
    </DemoSessionContext.Provider>
  );
}

export function useDemoSession() {
  const session = useContext(DemoSessionContext);
  if (!session) throw new Error('Demo session provider is missing.');
  return session;
}
