'use client';

import { useActionState } from 'react';

import { passwordLogin } from '@/lib/auth/actions';
import { initialAuthState } from '@/lib/auth/form-state';

/** Admins and staff sign in with a password; only customers use codes. */
export default function PasswordForm() {
  const [state, formAction, pending] = useActionState(passwordLogin, initialAuthState);

  return (
    <form action={formAction} noValidate>
      <label htmlFor="identifier">Email or phone</label>
      <input
        id="identifier"
        name="identifier"
        type="text"
        autoComplete="username"
        required
        autoFocus
      />

      <label htmlFor="password">Password</label>
      <input
        id="password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        aria-describedby={state.error ? 'login-error' : undefined}
      />

      {state.error && (
        <p id="login-error" role="alert">
          {state.error}
        </p>
      )}

      <button type="submit" disabled={pending}>
        {pending ? 'Signing in...' : 'Sign in'}
      </button>
    </form>
  );
}
