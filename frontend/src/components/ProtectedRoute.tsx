'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { useAuth } from '@/context/AuthContext';

/**
 * A second gate for pages that need a signed-in shopper.
 *
 * Middleware already redirects these routes, and the backend rejects the
 * calls behind them, so this exists to keep a stale client-side navigation
 * from flashing an empty page. There is no loading state: the session is
 * resolved on the server before the tree renders.
 */
export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isSignedIn } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isSignedIn) {
      router.replace('/signin');
    }
  }, [isSignedIn, router]);

  if (!isSignedIn) {
    return null;
  }

  return <>{children}</>;
}
