import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import PasswordForm from '@/components/auth/PasswordForm';
import { getCurrentUser } from '@/lib/auth/current-user';

export const metadata: Metadata = {
  title: 'Admin sign in',
  robots: { index: false, follow: false },
};

export default async function AdminLoginPage() {
  const user = await getCurrentUser();

  if (user?.role === 'ADMIN' || user?.role === 'STAFF') redirect('/admin');

  return (
    <main>
      <h1>Zeen admin</h1>

      <PasswordForm />
    </main>
  );
}
