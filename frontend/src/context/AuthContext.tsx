'use client';

import { createContext, useContext } from 'react';

import type { UserProfile } from '@/types/auth';

interface AuthContextType {
  user: UserProfile | null;
  isSignedIn: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

/**
 * The signed-in user, resolved on the server.
 *
 * Tokens live in httpOnly cookies, so nothing here can read them -- the
 * layout calls /auth/me while rendering and passes the profile down. There
 * is no client-side sign-in call to make: the OTP forms post to server
 * actions, which set the cookies and refresh the tree.
 */
export function AuthProvider({ user, children }: { user: UserProfile | null; children: React.ReactNode }) {
  return <AuthContext.Provider value={{ user, isSignedIn: user !== null }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }

  return context;
}
