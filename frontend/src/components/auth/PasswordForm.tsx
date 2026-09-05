'use client';

import { useActionState } from 'react';

import Button from '@/components/ui/Button';
import { Input } from '@/components/ui/Field';
import { passwordLogin } from '@/lib/auth/actions';
import { initialAuthState } from '@/lib/auth/form-state';

import { authStyles } from './AuthShell';

export default function PasswordForm() {
  const [state, formAction, pending] = useActionState(passwordLogin, initialAuthState);

  return (
    <form action={formAction} className={authStyles.form} noValidate>
      {state.error && <p className={authStyles.alert}>{state.error}</p>}

      <Input label="Email or phone" name="identifier" type="text" autoComplete="username" required autoFocus />

      <Input label="Password" name="password" type="password" autoComplete="current-password" required />

      <Button type="submit" size="lg" block disabled={pending}>
        {pending ? 'Signing in' : 'Sign in'}
      </Button>
    </form>
  );
}
