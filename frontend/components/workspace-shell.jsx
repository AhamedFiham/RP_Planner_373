'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';

export default function WorkspaceShell({ children }) {
  const pathname = usePathname();
  const isDfu = pathname === '/dfu';

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="home-header">
        <div className="home-header-inner">
          <Link className="home-brand" href="/dashboard" aria-label="DCare AI dashboard">
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
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/dfu" aria-current={isDfu ? 'page' : undefined}>DFU</Link>
            <Link href="/retino" aria-current={pathname === '/retino' ? 'page' : undefined}>Retinopathy</Link>
            <Link href="/members/1" aria-current={pathname === '/members/1' ? 'page' : undefined}>Member 1</Link>
            <Link href="/members/2" aria-current={pathname === '/members/2' ? 'page' : undefined}>Member 2</Link>
            <Link href="/members/3" aria-current={pathname === '/members/3' ? 'page' : undefined}>Member 3</Link>
          </nav>
        </div>
      </header>
      <main id="main-content" className={isDfu ? 'dfu-main' : 'container'} tabIndex={-1}>{children}</main>
      <footer className="home-footer">
        <span>DCare AI</span>
        <span>Student research project</span>
      </footer>
    </>
  );
}
