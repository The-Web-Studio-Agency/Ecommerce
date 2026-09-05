import { Suspense } from 'react';

import OtpVerification from '@/components/OtpVerification';

export default function OtpVerificationPage() {
  return (
    <Suspense fallback={null}>
      <OtpVerification />
    </Suspense>
  );
}
