import './globals.css';
import AuthProvider from '@/components/auth-provider';

export const metadata = {
  title: { default: 'RP Planner', template: '%s | RP Planner' },
  description: 'Research project workspace for DFU and four team members.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body><AuthProvider>{children}</AuthProvider></body>
    </html>
  );
}
