'use client';

import { useDemoSession } from './demo-session';

export default function WelcomeMessage() {
  const { user } = useDemoSession();
  return <p>Welcome, {user?.email.split('@')[0] || 'team member'}.</p>;
}
