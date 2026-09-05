'use server';

import { redirect } from 'next/navigation';

import { authApi } from '@/lib/api/auth';
import { ApiError, ApiUnreachableError } from '@/lib/api/errors';
import type { AuthFormState } from '@/lib/auth/form-state';
import { clearSession, getRefreshToken, setSession } from '@/lib/auth/session';

/**
 * Turn a failed call into something a form can show.
 *
 * Rate limiting and unreachability get their own wording because the
 * remedy differs -- one is "wait", the other is "the server is down".
 */
function toFormState(error: unknown): AuthFormState {
  if (error instanceof ApiError) {
    if (error.isRateLimited) {
      const wait = error.retryAfterSeconds;
      return {
        error: wait
          ? `Too many attempts. Try again in ${wait} seconds.`
          : 'Too many attempts. Try again shortly.',
      };
    }

    return { error: error.message, fieldErrors: error.fieldErrors() };
  }

  if (error instanceof ApiUnreachableError) {
    return { error: 'Could not reach Zeen. Check your connection and try again.' };
  }

  throw error;
}

/**
 * Send a login code.
 *
 * Doubles as resend: the backend has no separate endpoint, and each request
 * expires the previous code.
 */
export async function requestOtp(
  _previous: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const phone = String(formData.get('phone') ?? '').trim();

  if (!phone) {
    return { error: 'Enter your phone number.', fieldErrors: { phone: 'Required' } };
  }

  try {
    await authApi.requestOtp(phone);
  } catch (error) {
    return toFormState(error);
  }

  redirect(`/signin/verify?phone=${encodeURIComponent(phone)}`);
}

/**
 * Verify a code and start a session.
 *
 * A phone with no account gets one created here -- this is registration as
 * well as sign-in.
 */
export async function verifyOtp(
  _previous: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const phone = String(formData.get('phone') ?? '').trim();
  const otp = String(formData.get('otp') ?? '').trim();
  const next = String(formData.get('next') ?? '/account');

  if (!phone) return { error: 'Start again from the sign-in page.' };

  if (!/^\d{6}$/.test(otp)) {
    return { error: 'Enter the 6-digit code.', fieldErrors: { otp: 'Enter 6 digits' } };
  }

  try {
    const tokens = await authApi.verifyOtp(phone, otp);
    await setSession(tokens);
  } catch (error) {
    return toFormState(error);
  }

  redirect(safeRedirect(next));
}

/** Sign in an admin or staff member with a password. */
export async function passwordLogin(
  _previous: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const identifier = String(formData.get('identifier') ?? '').trim();
  const password = String(formData.get('password') ?? '');

  if (!identifier || !password) {
    return { error: 'Enter your email or phone, and your password.' };
  }

  try {
    const tokens = await authApi.adminLogin(identifier, password);
    await setSession(tokens);
  } catch (error) {
    return toFormState(error);
  }

  redirect('/admin');
}

/** End the session, revoking the refresh token server-side as well. */
export async function logout(): Promise<void> {
  const refreshToken = await getRefreshToken();

  if (refreshToken) {
    try {
      await authApi.logout(refreshToken);
    } catch {
      // The cookies still get cleared: a revoke that fails must not strand
      // someone in a session they have asked to leave.
    }
  }

  await clearSession();
  redirect('/');
}

/**
 * Only allow redirects to a path on this site.
 *
 * `next` arrives from the query string, so without this an attacker could
 * link to a sign-in that lands on their own domain afterwards.
 */
function safeRedirect(target: string): string {
  if (!target.startsWith('/') || target.startsWith('//')) return '/account';
  return target;
}
