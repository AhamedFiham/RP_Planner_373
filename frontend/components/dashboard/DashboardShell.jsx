'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { useAuth } from '@/components/auth-provider';
import {
  Activity, Bell, ClipboardList, Eye, Home, Menu, Search,
  ShieldCheck, Sparkles, Stethoscope, Utensils, X,
} from 'lucide-react';

const healthTools = [
  { href: '/dashboard/diabetes', label: 'Diabetes Prediction', icon: Activity },
  { href: '/dashboard/retinopathy', label: 'Retinopathy Analysis', icon: Eye },
  { href: '/dashboard/wound', label: 'Wound Healing', icon: ShieldCheck },
  { href: '/dashboard/diet', label: 'Diet Planner', icon: Utensils },
];

const healthLinks = [
  { href: '/dashboard#history', label: 'Health History', icon: ClipboardList },
  { href: '/dashboard#history', label: 'Reports', icon: Stethoscope },
  { href: '/dashboard#recommendations', label: 'Recommendations', icon: Sparkles },
];

function NavLink({ href, label, icon: Icon, active = false, onClick }) {
  return (
    <Link
      className={`dashboard-nav-link${active ? ' active' : ''}`}
      href={href}
      aria-current={active ? 'page' : undefined}
      onClick={onClick}
    >
      <Icon size={17} />{label}
    </Link>
  );
}

export default function DashboardShell({ children, title, contentAs: ContentElement = 'main', showSkipLink = true, hideSidebar = false }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { user, logout, dashboard = '/dashboard' } = useAuth() || {};
  const closeMenu = () => setOpen(false);

  return (
    <div className="dashboard-page">
      {showSkipLink && <a className="skip-link" href="#main-content">Skip to content</a>}
      {!hideSidebar && <aside className={`dashboard-sidebar ${open ? 'open' : ''}`}>
        <div className="dashboard-brand">
          <div className="brand-mark"><Sparkles size={18} /></div>
          <div><strong>DiabeticCARE</strong><span>Smart Diabetes Care</span></div>
          <button className="sidebar-close" type="button" onClick={closeMenu} aria-label="Close menu"><X size={20} /></button>
        </div>
        <nav className="dashboard-nav" aria-label="Dashboard navigation">
          <NavLink href={dashboard} label="My Dashboard" icon={Home} active={pathname === dashboard} onClick={closeMenu} />
          <p className="nav-label">AI Health Tools</p>
          {healthTools.map(tool => <NavLink key={tool.href} {...tool} active={pathname === tool.href} onClick={closeMenu} />)}
          <p className="nav-label">My Health</p>
          {healthLinks.map(link => <NavLink key={link.label} {...link} onClick={closeMenu} />)}
        </nav><button className="dashboard-logout" type="button" onClick={logout}><X size={17} /> Sign out</button>
      </aside>}
      {!hideSidebar && open && <button className="dashboard-overlay" type="button" onClick={closeMenu} aria-label="Close navigation" />}
      <ContentElement className="dashboard-content" id={showSkipLink ? 'main-content' : undefined} tabIndex={-1}>
        <header className="dashboard-topbar">
          {!hideSidebar && <button className="dashboard-menu" type="button" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={22} /></button>}
          <h1>{title}</h1>
          <div className="dashboard-top-actions">
            <label className="dashboard-search"><Search size={17} /><input aria-label="Search dashboard" placeholder="Search" /></label>
            <button className="icon-button" type="button" aria-label="Notifications"><Bell size={19} /><i /></button>
            <div className="dashboard-user"><span className="avatar">{(user?.username || 'U').slice(0,1).toUpperCase()}</span><span className="user-name">{user?.username || 'User'}</span></div>
          </div>
          {hideSidebar && <button type="button" className="text-button" onClick={logout}>Sign out</button>}
        </header>
        {children}
      </ContentElement>
    </div>
  );
}
