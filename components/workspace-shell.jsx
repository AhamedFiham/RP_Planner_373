'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useDemoSession } from './demo-session';

export default function WorkspaceShell({ children }) {
  const { user, ready, logout } = useDemoSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (ready && !user) router.replace('/login');
  }, [ready, user, router]);

  function handleLogout() {
    logout();
    router.replace('/login');
  }

  if (!ready || !user) {
    return <main className="container"><p role="status">Loading…</p></main>;
  }

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <div className="header-content">
          <Link className="site-name" href="/home">RP Planner</Link>
          <nav aria-label="Main navigation">
            <Link href="/home" aria-current={pathname === '/home' ? 'page' : undefined}>Home</Link>
            <button className="text-button" type="button" onClick={handleLogout}>Logout</button>
          </nav>
        </div>
      </header>
      <main id="main-content" className="container" tabIndex={-1}>{children}</main>
      <footer className="site-footer">RP Planner · Research project</footer>
    </>
  );
}
