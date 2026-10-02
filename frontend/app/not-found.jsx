import Link from 'next/link';

export default function NotFoundPage() {
  return (
    <main className="container">
      <h1>Page not found</h1>
      <p>This project section does not exist.</p>
      <Link className="button" href="/home">Back to home</Link>
    </main>
  );
}
