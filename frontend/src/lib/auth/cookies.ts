/**
 * Cookie names and options, kept free of next/headers so middleware can
 * share them. Middleware reads and writes cookies through the request and
 * response objects, which is a different API from the one server actions
 * use, but the names and options have to match.
 */

export const ACCESS_TOKEN_COOKIE = 'zeen_access_token';
export const REFRESH_TOKEN_COOKIE = 'zeen_refresh_token';

/**
 * A little under the backend's REFRESH_TOKEN_EXPIRE_DAYS of 14, so the
 * browser drops an expired cookie rather than sending one that is certain
 * to be rejected.
 */
export const REFRESH_MAX_AGE_SECONDS = 13 * 24 * 60 * 60;

export function sessionCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: 'lax' as const,
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge,
  };
}
