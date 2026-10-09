import './globals.css';

export const metadata = {
  title: { default: 'RP Planner', template: '%s | RP Planner' },
  description: 'Research project workspace for DFU and four team members.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
