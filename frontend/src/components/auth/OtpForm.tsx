'use client';

import { useActionState, useEffect, useState } from 'react';

import Button from '@/components/ui/Button';
import { Input } from '@/components/ui/Field';
import { requestOtp, verifyOtp } from '@/lib/auth/actions';
import { initialAuthState } from '@/lib/auth/form-state';

import { authStyles } from './AuthShell';

/** The backend allows five code requests per five minutes, so resend is paced. */
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

  const fieldError = state.fieldErrors?.otp;
  const formError = fieldError ? null : (state.error ?? resendState.error);

  return (
    <>
      <form action={formAction} className={authStyles.form} noValidate>
        {formError && <p className={authStyles.alert}>{formError}</p>}

        <input type="hidden" name="phone" value={phone} />
        <input type="hidden" name="next" value={next} />

        <Input
          label="6-digit code"
          name="otp"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          pattern="\d{6}"
          required
          autoFocus
          error={fieldError}
        />

        <Button type="submit" size="lg" block disabled={pending}>
          {pending ? 'Verifying' : 'Verify and continue'}
        </Button>
      </form>

      <form action={resendAction} className={authStyles.footnote}>
        <input type="hidden" name="phone" value={phone} />

        {secondsLeft > 0 ? (
          <span>Didn&rsquo;t get it? You can ask for another in {secondsLeft}s.</span>
        ) : (
          <span>
            Didn&rsquo;t get it?{' '}
            <button type="submit" className={authStyles.resend} disabled={resending}>
              Send a new code
            </button>
          </span>
        )}
      </form>
    </>
  );
}
