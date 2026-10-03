'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useDemoSession } from './demo-session';

export default function WorkspaceShell({ children }) {
  const { user, ready, logout } = useDemoSession();
  const router = useRouter();
  const pathname = usePathname();
  const isHome = pathname === '/home';
  const usesResearchHeader = isHome || pathname === '/dfu';

  useEffect(() => {
    if (ready && !user) router.replace('/dashboard');
  }, [ready, user, router]);

  function handleLogout() {
    logout();
    router.replace('/dashboard');
  }

  if (!ready || !user) {
    return <main className="container"><p role="status">Loading…</p></main>;
  }

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      {usesResearchHeader ? (
        <>
          <header className="home-header">
            <div className="home-header-inner">
              <Link className="home-brand" href="/home" aria-label="DCare AI home">
                <Image
                  className="home-brand-image"
                  src="/dcare-ai-logo.png"
                  alt="DCare AI"
                  width={1970}
                  height={452}
                  priority
                />
              </Link>
              <nav className="home-nav" aria-label="Research sections">
                <Link href="/dfu" aria-current={pathname === '/dfu' ? 'page' : undefined}>DFU</Link>
                <Link href="/retino">Retinopathy</Link>
                <Link href="/members/1">Member 1</Link>
                <Link href="/members/2">Member 2</Link>
                <Link href="/members/3">Member 3</Link>
              </nav>
              <details className="home-account">
                <summary aria-label="Account menu" title="Account menu">
                  <svg viewBox="0 0 40 40" aria-hidden="true" focusable="false">
                    <circle cx="20" cy="20" r="18" fill="currentColor" />
                    <circle cx="20" cy="15" r="6" fill="#fff" />
                    <path d="M9 30c2.1-6 6-9 11-9s8.9 3 11 9" fill="#fff" />
                  </svg>
                </summary>
                <div className="home-account-panel">
                  <p className="home-account-email">{user.email}</p>
                  <button type="button" onClick={handleLogout}>Sign out</button>
                </div>
              </details>
            </div>
          </header>
          <main id="main-content" className={isHome ? 'home-main' : 'dfu-main'} tabIndex={-1}>{children}</main>
          <footer className="home-footer">
            <span>DCare AI</span>
            <span>Student research project</span>
          </footer>
        </>
      ) : (
        <>
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
      )}
    </>
  );
}
