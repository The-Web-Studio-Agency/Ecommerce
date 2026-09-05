import { NextResponse, type NextRequest } from 'next/server';

import { authApi } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/errors';
import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_MAX_AGE_SECONDS,
  REFRESH_TOKEN_COOKIE,
  sessionCookieOptions,
} from '@/lib/auth/cookies';

/**
 * Routes that need a signed-in customer.
 *
 * /cart is deliberately absent: guests keep a cookie-backed cart that is
 * merged after sign-in, so they have to be able to see it.
 */
const CUSTOMER_PREFIXES = ['/account', '/orders', '/checkout', '/wishlist'];

/** Routes that need a staff or admin role. */
const ADMIN_PREFIX = '/admin';

/** The admin sign-in page itself must stay reachable while signed out. */
const ADMIN_LOGIN = '/admin/login';

function matches(pathname: string, prefixes: string[]): boolean {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
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

  const needsCustomer = matches(pathname, CUSTOMER_PREFIXES);
  const needsStaff = matches(pathname, [ADMIN_PREFIX]) && pathname !== ADMIN_LOGIN;

  let accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value ?? null;
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value ?? null;

  let refreshed: { access: string; refresh: string; expiresIn: number } | null = null;
  let refreshFailed = false;

  // The access cookie expires on its own, so its absence next to a refresh
  // cookie is the signal to rotate.
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

  const response =
    (await guard({ request, pathname, search, accessToken, needsCustomer, needsStaff })) ??
    NextResponse.next();

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

async function guard(context: {
  request: NextRequest;
  pathname: string;
  search: string;
  accessToken: string | null;
  needsCustomer: boolean;
  needsStaff: boolean;
}): Promise<NextResponse | null> {
  const { request, pathname, search, accessToken, needsCustomer, needsStaff } = context;

  if (!needsCustomer && !needsStaff) return null;

  if (!accessToken) {
    return redirectToSignIn(request, pathname, search, needsStaff);
  }

  if (!needsStaff) return null;

  // Role has to come from the backend rather than from reading the token
  // here: middleware holds no signing key, so a decoded payload would be
  // unverified input.
  try {
    const user = await authApi.me(accessToken);

    if (user.role !== 'ADMIN' && user.role !== 'STAFF') {
      const url = request.nextUrl.clone();
      url.pathname = '/';
      url.search = '';
      return NextResponse.redirect(url);
    }
  } catch (error) {
    if (error instanceof ApiError && (error.isUnauthenticated || error.isForbidden)) {
      return redirectToSignIn(request, pathname, search, true);
    }
    throw error;
  }

  return null;
}

function redirectToSignIn(
  request: NextRequest,
  pathname: string,
  search: string,
  needsStaff: boolean,
): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = needsStaff ? ADMIN_LOGIN : '/signin';
  url.search = needsStaff ? '' : `?next=${encodeURIComponent(pathname + search)}`;

  return NextResponse.redirect(url);
}

export const config = {
  matcher: [
    /*
     * Everything except Next's own assets and files with an extension, so
     * the refresh runs on navigations rather than on every image request.
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.).*)',
  ],
};
