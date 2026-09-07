'use client';

import Link from 'next/link';
import { useActionState } from 'react';

import { requestOtp } from '@/lib/auth/actions';
import { initialAuthState } from '@/lib/auth/form-state';

/**
 * Sign in with a phone number.
 *
 * The backend authenticates customers with a code sent by SMS -- there is
 * no customer password login, and no email route to a code -- so this asks
 * for a phone and nothing else. Verifying the code both signs an existing
 * shopper in and creates an account for a new one.
 */
export default function SignIn() {
  const [state, formAction, pending] = useActionState(requestOtp, initialAuthState);

  return (
    <div className="login-page-wrapper">
      <div className="login-page-card">
        <div className="login-page-grid">
          {/* ================= LEFT IMAGE ================= */}

          <div className="login-page-image-panel">
            <img
              src="/assets/cloth-0.webp"
              alt="Portrait against a light neutral backdrop"
              className="login-page-image"
    
            />
          </div>

          {/* ================= RIGHT FORM ================= */}

          <div className="login-page-form-panel">
            <div className="login-page-form-inner">
              <h1 className="login-page-heading">Sign in</h1>

              <p className="login-page-subtext">
                Don&rsquo;t have an account?{' '}
                <Link href="/signup" className="login-page-signup-link">
                  Sign up
                </Link>
              </p>

              {/* ================= LOGIN FORM ================= */}

              <form className="login-page-fields" action={formAction} noValidate>
                {/* Phone */}

                <div>
                  <input
                    type="tel"
                    name="phone"
                    placeholder="Phone number"
                    maxLength={15}
                    inputMode="numeric"
                    autoComplete="tel"
                    className="login-page-input"
                  />

                  {(state.fieldErrors?.phone || state.error) && (
                    <p className="login-page-error">{state.fieldErrors?.phone ?? state.error}</p>
                  )}
                </div>

                {/* Submit */}

                <button type="submit" className="login-page-submit-button" disabled={pending}>
                  {pending ? 'Sending OTP...' : 'Continue'}
                </button>
              </form>

              {/* ================= DIVIDER ================= */}

              <div className="login-page-divider">
                <span className="login-page-divider-line" />

                <span className="login-page-divider-text">Or continue with</span>

                <span className="login-page-divider-line" />
              </div>

              {/* ================= GOOGLE ================= */}

              <div className="login-page-oauth-grid">
                <button
                  className="login-page-oauth-button"
                  type="button"
                  onClick={() => {
                    console.log('Google sign in');
                    // Add your Google authentication logic here
                  }}>
                  <GoogleIcon />
                  Google
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ========================= Google Icon ========================= */

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1v-.01z"
      />

      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.66-2.25 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A10.99 10.99 0 0 0 12 23z"
      />

      <path
        fill="#FBBC05"
        d="M5.84 14.09A6.6 6.6 0 0 1 5.5 12c0-.73.12-1.43.34-2.09V7.07H2.18A10.99 10.99 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z"
      />

      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1a10.99 10.99 0 0 0-9.82 6.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

