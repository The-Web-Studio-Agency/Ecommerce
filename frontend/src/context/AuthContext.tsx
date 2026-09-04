'use client';

import { createContext, useContext, useEffect, useState } from 'react';

interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const [loading, setLoading] = useState(true);

  const signIn = (user: User) => {
    setUser(user);
  };

//   useEffect(() => {
//     const fetchCurrentUser = async () => {
//       try {
        /*
      const response = await fetch("BACKEND_ME_URL", {
        method: "GET",
        credentials: "include",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Failed to fetch user");
      }

      setUser(data.user);
      */
//       } catch (error) {
//         console.error('Failed to fetch current user:', error);
//       } finally {
//         setLoading(false);
//       }
//     };

//     fetchCurrentUser();
//   }, []);

  return <AuthContext.Provider value={{ user, loading, signIn }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
