'use client';

import { useActionState } from 'react';

import Button from '@/components/ui/Button';
import { Input } from '@/components/ui/Field';
import { requestOtp } from '@/lib/auth/actions';
import { initialAuthState } from '@/lib/auth/form-state';

import { authStyles } from './AuthShell';

export default function PhoneForm() {
  const [state, formAction, pending] = useActionState(requestOtp, initialAuthState);

  const fieldError = state.fieldErrors?.phone;
  const formError = fieldError ? null : state.error;

  return (
    <form action={formAction} className={authStyles.form} noValidate>
      {formError && <p className={authStyles.alert}>{formError}</p>}

      <Input
        label="Mobile number"
        name="phone"
        type="tel"
        inputMode="numeric"
        autoComplete="tel"
        placeholder="10-digit number"
        required
        autoFocus
        error={fieldError}
      />

      <Button type="submit" size="lg" block disabled={pending}>
        {pending ? 'Sending code' : 'Send code'}
      </Button>
    </form>
  );
}
