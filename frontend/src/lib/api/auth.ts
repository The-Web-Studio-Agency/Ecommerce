import { apiRequest } from '@/lib/api/client';
import type { Tenant, TokenPair, UserProfile } from '@/types/auth';

export const authApi = {
  /**
   * Send a login code to a customer's phone.
   *
   * Also serves as resend -- there is no separate endpoint, and each call
   * expires the previous code. Rate limited to 5 per 5 minutes per phone.
   */
  requestOtp(phone: string): Promise<null> {
    return apiRequest<null>('/auth/otp/request', {
      method: 'POST',
      body: { phone },
      cache: 'no-store',
    });
  },

  /**
   * Verify a code and receive a token pair.
   *
   * This is registration as well as sign-in: a phone with no account gets
   * one created on the first successful verification.
   */
  verifyOtp(phone: string, otp: string): Promise<TokenPair> {
    return apiRequest<TokenPair>('/auth/otp/verify', {
      method: 'POST',
      body: { phone, otp },
      cache: 'no-store',
    });
  },

  /** Admins and staff authenticate with a password, not a code. */
  adminLogin(identifier: string, password: string): Promise<TokenPair> {
    return apiRequest<TokenPair>('/admin/auth/login', {
      method: 'POST',
      body: { identifier, password },
      cache: 'no-store',
    });
  },

  staffLogin(identifier: string, password: string): Promise<TokenPair> {
    return apiRequest<TokenPair>('/staff/auth/login', {
      method: 'POST',
      body: { identifier, password },
      cache: 'no-store',
    });
  },

  /** Rotate a refresh token. Reusing a revoked one revokes every session. */
  refresh(refreshToken: string): Promise<TokenPair> {
    return apiRequest<TokenPair>('/auth/refresh', {
      method: 'POST',
      body: { refresh_token: refreshToken },
      cache: 'no-store',
    });
  },

  logout(refreshToken: string): Promise<null> {
    return apiRequest<null>('/auth/logout', {
      method: 'POST',
      body: { refresh_token: refreshToken },
      cache: 'no-store',
    });
  },

  me(token: string): Promise<UserProfile> {
    return apiRequest<UserProfile>('/auth/me', { token, cache: 'no-store' });
  },

  /** Erase the account. Past orders survive, stripped of the person. */
  deleteAccount(token: string): Promise<null> {
    return apiRequest<null>('/auth/me', { method: 'DELETE', token, cache: 'no-store' });
  },

  listTenants(): Promise<Tenant[]> {
    return apiRequest<Tenant[]>('/auth/tenants', { cache: 'no-store' });
  },
};
