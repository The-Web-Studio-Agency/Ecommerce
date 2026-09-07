'use client';

import { useTransition } from 'react';

import { logout } from '@/lib/auth/actions';

/** Ends the session, revoking the refresh token server-side as well. */
export default function SignOutButton() {
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => startTransition(() => logout())}
      className="myorderFilterButton">
      {pending ? 'Signing out...' : 'Sign out'}
    </button>
  );
}
