import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

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
    <main>
      <h1>Sign in to Zeen</h1>
      <p>We&rsquo;ll text you a code. New here? Your account is created automatically.</p>

      <PhoneForm />
    </main>
  );
}
