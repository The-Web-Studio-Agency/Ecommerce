import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import AuthShell from '@/components/auth/AuthShell';
import PhoneForm from '@/components/auth/PhoneForm';
import { getCurrentUser } from '@/lib/auth/current-user';

export const metadata: Metadata = {
  title: 'Sign in',
  robots: { index: false, follow: false },
};

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const user = await getCurrentUser();
  const { next } = await searchParams;

  if (user) {
    redirect(next && next.startsWith('/') && !next.startsWith('//') ? next : '/account');
  }

  return (
    <AuthShell title="Sign in" lede="We'll text you a code. If you're new, your account is created as you go.">
      <PhoneForm />
    </AuthShell>
  );
}
