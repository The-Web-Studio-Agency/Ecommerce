import { cookies } from 'next/headers';

import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_MAX_AGE_SECONDS,
  REFRESH_TOKEN_COOKIE,
  sessionCookieOptions,
} from '@/lib/auth/cookies';
import type { TokenPair } from '@/types/auth';

/**
 * Tokens are held in httpOnly cookies rather than localStorage.
 *
 * The backend hands them back in the response body, so something has to
 * store them. Cookies are the only store middleware and server components
 * can both read, which is what lets a route be refused before it renders
 * and lets pages fetch their own data. httpOnly keeps them away from any
 * script on the page.
 */

export async function getAccessToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(ACCESS_TOKEN_COOKIE)?.value ?? null;
}

export async function getRefreshToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(REFRESH_TOKEN_COOKIE)?.value ?? null;
}

/**
 * Persist a token pair.
 *
 * Only callable from a server action or route handler -- Next forbids
 * writing cookies while rendering, which is why refresh runs in middleware.
 */
export async function setSession(tokens: TokenPair): Promise<void> {
  const store = await cookies();

  store.set(ACCESS_TOKEN_COOKIE, tokens.access_token, sessionCookieOptions(tokens.expires_in));
  store.set(
    REFRESH_TOKEN_COOKIE,
    tokens.refresh_token,
    sessionCookieOptions(REFRESH_MAX_AGE_SECONDS),
  );
}

export async function clearSession(): Promise<void> {
  const store = await cookies();

  store.delete(ACCESS_TOKEN_COOKIE);
  store.delete(REFRESH_TOKEN_COOKIE);
}

export { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE };
