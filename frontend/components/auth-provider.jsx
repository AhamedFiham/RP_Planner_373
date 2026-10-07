'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export default function AuthProvider({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [token, setToken] = useState(null);
  const [ready, setReady] = useState(false);
  useEffect(() => { setToken(window.localStorage.getItem('dcare_token')); setReady(true); }, []);
  useEffect(() => {
    if (ready && pathname !== '/login' && !token) router.replace('/login');
    if (ready && pathname === '/login' && token) router.replace('/dashboard');
  }, [ready, token, pathname, router]);
  const logout = () => { window.localStorage.removeItem('dcare_token'); setToken(null); router.replace('/login'); };
  const signIn = (accessToken) => {
    window.localStorage.setItem('dcare_token', accessToken);
    setToken(accessToken);
    router.replace('/dashboard');
  };
  return <AuthContext.Provider value={{ token, ready, signIn, logout }}>{children}</AuthContext.Provider>;
}
