// src/context/AuthContext.tsx

'use client';

import React, { createContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useRouter } from 'next/navigation';

interface AuthContextType {
  isAuthenticated: boolean;
  setIsAuthenticated: (auth: boolean) => void;
}

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  setIsAuthenticated: () => {},
});

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const router = useRouter();

  // Funkcja opakowująca fetch, zapamiętywana dzięki useCallback
  const customFetch = useCallback(async (url: string, options?: RequestInit) => {
    const response = await fetch(url, { credentials: 'include', ...options });
    // Jeśli status 401 i endpoint nie zawiera "/auth/me", przekieruj na stronę główną
    if (!response.ok && response.status === 401 && !url.includes('/auth/me')) {
      router.push('/');
    }
    return response;
  }, [router]);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const API_BASE_URL =
          process.env.NEXT_PUBLIC_API_FLASK_URL ||
          'https://torch-ed-production.up.railway.app/api/v1';

        const authUrl = `${API_BASE_URL}/auth/me`;
        console.log('Auth Request URL:', authUrl);
        console.log('Available cookies:', document.cookie);

        // Używamy customFetch – dla endpointu /auth/me przekierowanie nie nastąpi
        const res = await customFetch(authUrl);
        console.log('Auth Response status:', res.status);
        console.log('Auth Response status text:', res.statusText);

        if (res.ok) {
          setIsAuthenticated(true);
          console.log('User authenticated successfully.');
        } else {
          setIsAuthenticated(false);
          console.log('User not authenticated.');
        }
      } catch (err: unknown) {
        console.error('Error verifying session:', err);
        setIsAuthenticated(false);
      }
    };

    void checkSession();
  }, [customFetch]);

  return (
    <AuthContext.Provider value={{ isAuthenticated, setIsAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};
