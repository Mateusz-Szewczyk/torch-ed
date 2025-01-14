// src/context/AuthContext.tsx

'use client';

import React, { createContext, useState, useEffect, ReactNode } from 'react';

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

  useEffect(() => {
    const checkSession = async () => {
      try {
        const API_BASE_URL =
          process.env.NEXT_PUBLIC_API_FLASK_URL ||
          'https://torch-ed-production.up.railway.app/api/v1';

        // Logowanie URL i dostępnych ciasteczek
        console.log('Auth Request URL:', `${API_BASE_URL}/auth/me`);
        console.log('Available cookies:', document.cookie);

        const res = await fetch(`${API_BASE_URL}/auth/me`, {
          credentials: 'include',
        });

        // Logowanie statusu odpowiedzi
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

    checkSession();
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, setIsAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};
