'use client';

import { useActionState } from 'react';

import { requestOtp } from '@/lib/auth/actions';
import { initialAuthState } from '@/lib/auth/form-state';

/**
 * Step one of sign-in: the phone number.
 *
 * There is no separate registration -- a number without an account gets one
 * when its first code is verified, so this form is both sign-in and sign-up.
 */
export default function PhoneForm() {
  const [state, formAction, pending] = useActionState(requestOtp, initialAuthState);

  return (
    <form action={formAction} noValidate>
      <label htmlFor="phone">Mobile number</label>

      <input
        id="phone"
        name="phone"
        type="tel"
        inputMode="numeric"
        autoComplete="tel"
        required
        autoFocus
        aria-describedby={state.fieldErrors?.phone || state.error ? 'phone-error' : undefined}
        aria-invalid={Boolean(state.fieldErrors?.phone)}
      />

      {(state.fieldErrors?.phone || state.error) && (
        <p id="phone-error" role="alert">
          {state.fieldErrors?.phone ?? state.error}
        </p>
      )}

      <button type="submit" disabled={pending}>
        {pending ? 'Sending code...' : 'Send code'}
      </button>
    </form>
  );
}
