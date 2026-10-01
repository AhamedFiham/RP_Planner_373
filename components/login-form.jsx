'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useDemoSession } from './demo-session';

export default function LoginForm() {
  const router = useRouter();
  const { user, ready, login } = useDemoSession();
  const [error, setError] = useState('');

  useEffect(() => {
    if (ready && user) router.replace('/home');
  }, [ready, user, router]);

  function handleSubmit(event) {
    event.preventDefault();
    setError('');
    const form = event.currentTarget;
    const email = form.elements.email.value.trim();
    if (!form.elements.password.value.trim()) {
      setError('Please enter a password.');
      form.elements.password.focus();
      return;
    }
    try {
      login(email);
      form.elements.password.value = '';
      router.replace('/home');
    } catch {
      setError('Your browser could not start a session. Allow site storage and try again.');
    }
  }

  if (!ready || user) return <p role="status">Loading…</p>;

  return (
    <>
      <form onSubmit={handleSubmit}>
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="username" placeholder="name@example.com" required />
        <label htmlFor="password">Password</label>
        <input id="password" name="password" type="password" autoComplete="current-password" required />
        {error && <p className="error" role="alert">{error}</p>}
        <button className="button login-button" type="submit">Login</button>
      </form>
      <p className="demo-note">Demo login: use any valid email and a non-empty password. Accounts are not verified yet.</p>
    </>
  );
}
