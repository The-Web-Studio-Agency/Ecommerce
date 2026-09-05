import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import OtpForm from '@/components/auth/OtpForm';

export const metadata: Metadata = {
  title: 'Enter your code',
  robots: { index: false, follow: false },
};

export default async function VerifyPage({
  searchParams,
}: {
  searchParams: Promise<{ phone?: string; next?: string }>;
}) {
  const { phone, next } = await searchParams;

  // Without a number there is nothing to verify against, so start over
  // rather than showing a form that cannot succeed.
  if (!phone) redirect('/signin');

  const destination = next && next.startsWith('/') && !next.startsWith('//') ? next : '/account';

  return (
    <main>
      <h1>Enter your code</h1>
      <p>We sent a 6-digit code to {phone}.</p>

      <OtpForm phone={phone} next={destination} />
    </main>
  );
}
