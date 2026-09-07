import { NextResponse, type NextRequest } from 'next/server';

import { authApi } from '@/lib/api/auth';
import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_MAX_AGE_SECONDS,
  REFRESH_TOKEN_COOKIE,
  sessionCookieOptions,
} from '@/lib/auth/cookies';

/**
 * Routes that need a signed-in customer.
 *
 * /cart-items is deliberately absent: guests keep a cookie-backed cart that
 * is merged after sign-in, so they have to be able to see it.
 */
const CUSTOMER_PREFIXES = [
  '/my-account',
  '/my-orders',
  '/check-out',
  '/order-success',
  '/invoice',
  '/payment-history',
];

function matches(pathname: string, prefixes: string[]): boolean {
  return prefixes.some(prefix => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

/**
 * Refresh the session and guard protected routes.
 *
 * Refresh has to happen here because Next forbids writing cookies while
 * rendering: a server component can read the access token but cannot
 * replace an expired one. Middleware runs before rendering and can set
 * cookies on the response, so it is the only place a rotation can be
 * persisted.
 *
 * Guarding here is a first gate, not the authority. Every protected call
 * is checked again by the backend against the role on the token, so a
 * bypass of this check still fails at the API.
 */
export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  let accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value ?? null;
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value ?? null;

  let refreshed: { access: string; refresh: string; expiresIn: number } | null = null;
  let refreshFailed = false;

  /* The access cookie expires on its own, so its absence next to a refresh
     cookie is the signal to rotate. */
  if (!accessToken && refreshToken) {
    try {
      const tokens = await authApi.refresh(refreshToken);
      accessToken = tokens.access_token;
      refreshed = {
        access: tokens.access_token,
        refresh: tokens.refresh_token,
        expiresIn: tokens.expires_in,
      };
    } catch {
      accessToken = null;
      refreshFailed = true;
    }
  }

  let response: NextResponse;

  if (matches(pathname, CUSTOMER_PREFIXES) && !accessToken) {
    const url = request.nextUrl.clone();
    url.pathname = '/signin';
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    response = NextResponse.redirect(url);
  } else {
    response = NextResponse.next();
  }

  if (refreshed) {
    response.cookies.set(
      ACCESS_TOKEN_COOKIE,
      refreshed.access,
      sessionCookieOptions(refreshed.expiresIn),
    );
    response.cookies.set(
      REFRESH_TOKEN_COOKIE,
      refreshed.refresh,
      sessionCookieOptions(REFRESH_MAX_AGE_SECONDS),
    );
  }

  if (refreshFailed) {
    response.cookies.delete(ACCESS_TOKEN_COOKIE);
    response.cookies.delete(REFRESH_TOKEN_COOKIE);
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Everything except Next's own assets and files with an extension, so
     * the refresh runs on navigations rather than on every image request.
     */
    '/((?!_next/static|_next/image|favicon.ico|assets|.*\\.).*)',
  ],
};
