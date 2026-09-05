import { cookies } from 'next/headers';

import type { TokenPair } from '@/types/auth';

export const ACCESS_TOKEN_COOKIE = 'zeen_access_token';
export const REFRESH_TOKEN_COOKIE = 'zeen_refresh_token';

/**
 * Refresh tokens live as long as the backend's REFRESH_TOKEN_EXPIRE_DAYS.
 * Kept a little shorter so an expired cookie is dropped by the browser
 * rather than sent and rejected.
 */
const REFRESH_MAX_AGE_SECONDS = 13 * 24 * 60 * 60;

/**
 * Tokens are held in httpOnly cookies rather than localStorage.
 *
 * The backend hands them back in the response body, so something has to
 * store them. Cookies are the only option readable by middleware and server
 * components, which is what lets a route be protected before it renders and
 * lets pages fetch their own data. httpOnly keeps them away from any script
 * on the page.
 */
function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: 'lax' as const,
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge,
  };
}

/** The access token for the current request, if the visitor has one. */
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
 * Only callable from a Server Action or Route Handler; Next forbids writing
 * cookies while rendering, which is why token refresh happens in middleware.
 */
export async function setSession(tokens: TokenPair): Promise<void> {
  const store = await cookies();

  store.set(ACCESS_TOKEN_COOKIE, tokens.access_token, cookieOptions(tokens.expires_in));
  store.set(REFRESH_TOKEN_COOKIE, tokens.refresh_token, cookieOptions(REFRESH_MAX_AGE_SECONDS));
}

export async function clearSession(): Promise<void> {
  const store = await cookies();

  store.delete(ACCESS_TOKEN_COOKIE);
  store.delete(REFRESH_TOKEN_COOKIE);
}
