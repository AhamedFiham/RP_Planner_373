'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

const safeDashboard = (value) => ['/dashboard', '/dashboard/diabetes', '/dashboard/retinopathy', '/dashboard/wound', '/dashboard/diet'].includes(value) ? value : '/dashboard';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export default function AuthProvider({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [dashboard, setDashboard] = useState('/dashboard');
  const [ready, setReady] = useState(false);
  useEffect(() => { setToken(window.localStorage.getItem('dcare_token')); setDashboard(safeDashboard(window.localStorage.getItem('dcare_dashboard'))); try { setUser(JSON.parse(window.localStorage.getItem('dcare_user') || 'null')); } catch { setUser(null); } setReady(true); }, []);
  useEffect(() => {
    if (ready && pathname !== '/login' && !token) router.replace('/login');
    if (ready && pathname === '/login' && token) router.replace(dashboard);
  }, [ready, token, pathname, router, dashboard]);
  const logout = () => { window.localStorage.removeItem('dcare_token'); window.localStorage.removeItem('dcare_dashboard'); window.localStorage.removeItem('dcare_user'); setUser(null); setToken(null); router.replace('/login'); };
  const signIn = (accessToken, target, profile) => {
    setUser(profile);
    window.localStorage.setItem('dcare_user', JSON.stringify(profile || null));
    const destination = safeDashboard(target);
    window.localStorage.setItem('dcare_dashboard', destination);
    setDashboard(destination);
    window.localStorage.setItem('dcare_token', accessToken);
    setToken(accessToken);
    router.replace(destination);
  };
  return <AuthContext.Provider value={{ user, token, ready, dashboard, signIn, logout }}>{children}</AuthContext.Provider>;
}
