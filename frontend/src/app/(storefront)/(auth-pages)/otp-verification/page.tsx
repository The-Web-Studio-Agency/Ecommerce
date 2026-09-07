import { Suspense } from 'react';

import OtpVerification from '@/components/OtpVerification';

/**
 * The phone to verify arrives in the query string, and reading it with
 * useSearchParams opts the page out of prerendering unless the boundary is
 * here -- without it the production build fails on this route.
 */
export default function OtpVerificationPage() {
  return (
    <Suspense>
      <OtpVerification />
    </Suspense>
  );
}
