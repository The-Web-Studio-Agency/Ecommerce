'use client';

import { useActionState, useEffect, useState } from 'react';

import { requestOtp, verifyOtp } from '@/lib/auth/actions';
import { initialAuthState } from '@/lib/auth/form-state';

/** The backend allows 5 code requests per 5 minutes, so resend is paced. */
const RESEND_COOLDOWN_SECONDS = 60;

export default function OtpForm({ phone, next }: { phone: string; next: string }) {
  const [state, formAction, pending] = useActionState(verifyOtp, initialAuthState);
  const [resendState, resendAction, resending] = useActionState(requestOtp, initialAuthState);
  const [secondsLeft, setSecondsLeft] = useState(RESEND_COOLDOWN_SECONDS);

  useEffect(() => {
    if (secondsLeft <= 0) return;

    const timer = setTimeout(() => setSecondsLeft((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  const error = state.fieldErrors?.otp ?? state.error ?? resendState.error;

  return (
    <>
      <form action={formAction} noValidate>
        <input type="hidden" name="phone" value={phone} />
        <input type="hidden" name="next" value={next} />

        <label htmlFor="otp">6-digit code</label>

        <input
          id="otp"
          name="otp"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          pattern="\d{6}"
          required
          autoFocus
          aria-describedby={error ? 'otp-error' : undefined}
          aria-invalid={Boolean(error)}
        />

        {error && (
          <p id="otp-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={pending}>
          {pending ? 'Verifying...' : 'Verify and continue'}
        </button>
      </form>

      <form action={resendAction}>
        <input type="hidden" name="phone" value={phone} />

        <button
          type="submit"
          disabled={resending || secondsLeft > 0}
          onClick={() => setSecondsLeft(RESEND_COOLDOWN_SECONDS)}
        >
          {secondsLeft > 0 ? `Resend code in ${secondsLeft}s` : 'Resend code'}
        </button>
      </form>
    </>
  );
}
