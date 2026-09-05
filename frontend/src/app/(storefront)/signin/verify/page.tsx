import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import AuthShell from '@/components/auth/AuthShell';
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

  // Without a number there is nothing to verify, so start over rather than
  // showing a form that cannot succeed.
  if (!phone) redirect('/signin');

  const destination = next && next.startsWith('/') && !next.startsWith('//') ? next : '/account';

  return (
    <AuthShell title="Enter your code" lede={`We sent a 6-digit code to ${phone}.`}>
      <OtpForm phone={phone} next={destination} />
    </AuthShell>
  );
}
