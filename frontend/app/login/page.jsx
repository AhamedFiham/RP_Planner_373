import LoginForm from '@/components/login-form';

export const metadata = { title: 'Login' };

export default function LoginPage() {
  return (
    <main className="login-page">
      <div className="login-box">
        <p className="site-name">RP Planner</p>
        <h1>Login</h1>
        <p className="muted">Sign in to your research project workspace.</p>
        <LoginForm />
      </div>
    </main>
  );
}
