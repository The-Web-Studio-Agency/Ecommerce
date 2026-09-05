import Link from 'next/link';

export const metadata = {
  title: 'Page not found',
};

export default function NotFound() {
  return (
    <main>
      <h1>Page not found</h1>
      <p>The page you were looking for is not here.</p>
      <Link href="/">Back to the shop</Link>
    </main>
  );
}
