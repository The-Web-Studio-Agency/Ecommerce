import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import SignOutButton from '@/components/auth/SignOutButton';
import { getCurrentUser } from '@/lib/auth/current-user';

export const metadata: Metadata = {
  title: 'Admin',
  robots: { index: false, follow: false },
};

export default async function AdminHomePage() {
  const user = await getCurrentUser();

  // Middleware checks the role first; this repeats it server-side so the
  // page cannot render for a customer even if that gate is bypassed.
  if (!user) redirect('/admin/login');
  if (user.role !== 'ADMIN' && user.role !== 'STAFF') redirect('/');

  return (
    <main>
      <h1>Zeen admin</h1>
      <p>Signed in as {user.email ?? user.phone} ({user.role}).</p>

      <SignOutButton />
    </main>
  );
}
