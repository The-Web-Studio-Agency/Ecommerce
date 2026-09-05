import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import SignOutButton from '@/components/auth/SignOutButton';
import { getCurrentUser } from '@/lib/auth/current-user';

export const metadata: Metadata = {
  title: 'Your account',
  robots: { index: false, follow: false },
};

export default async function AccountPage() {
  const user = await getCurrentUser();

  // Middleware turns guests away first; this is the server-side check that
  // holds even if that gate is bypassed.
  if (!user) redirect('/signin?next=/account');

  return (
    <main>
      <h1>Your account</h1>

      <dl>
        <dt>Phone</dt>
        <dd>{user.phone}</dd>

        <dt>Name</dt>
        <dd>{user.name ?? 'Not set'}</dd>

        <dt>Email</dt>
        <dd>{user.email ?? 'Not set'}</dd>
      </dl>

      <SignOutButton />
    </main>
  );
}
