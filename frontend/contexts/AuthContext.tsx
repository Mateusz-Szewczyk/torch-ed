'use client';

import React, {
  createContext,
  useState,
  useEffect,
  ReactNode,
  useCallback
} from 'react';
import { useRouter, usePathname } from 'next/navigation';

interface AuthContextType {
  isAuthenticated: boolean;
  setIsAuthenticated: (auth: boolean) => void;
  accessDenied: boolean;
  tokenExpired: boolean;
  setTokenExpired: (flag: boolean) => void;
  setAccessDenied: (flag: boolean) => void;
}

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  setIsAuthenticated: () => {},
  accessDenied: false,
  tokenExpired: false,
  setTokenExpired: () => {},
  setAccessDenied: () => {},
});

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [accessDenied, setAccessDenied] = useState<boolean>(false);
  const [tokenExpired, setTokenExpired] = useState<boolean>(false);
  const router = useRouter();
  const pathname = usePathname();

  // Funkcja opakowująca fetch używana do weryfikacji sesji
  const customFetch = useCallback(async (url: string, options?: RequestInit) => {
    return await fetch(url, { credentials: 'include', ...options });
  }, []);

  // Sprawdzenie sesji przy montowaniu komponentu
  useEffect(() => {
    const checkSession = async () => {
      try {
        const API_BASE_URL =
          process.env.NEXT_PUBLIC_API_FLASK_URL ||
          'http://localhost:14440/api/v1';

        const authUrl = `${API_BASE_URL}/auth/login`;
        console.log('Auth Request URL:', authUrl);
        console.log('Available cookies:', document.cookie);

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
      } finally {
        setIsLoading(false);
      }
    };

    void checkSession();
  }, [customFetch]);

  // Globalne przechwytywanie fetch – jeżeli którykolwiek endpoint zwróci 401 i użytkownik jest zalogowany,
  // wywołujemy wylogowanie z komunikatem o nieaktywności.
  useEffect(() => {
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const response = await originalFetch(...args);
      if (response.status === 401 && isAuthenticated) {
        console.warn('Received 401 – wylogowanie z powodu nieaktywności.');
        setIsAuthenticated(false);
        setTokenExpired(true);
        router.push('/');
      }
      return response;
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, [isAuthenticated, router]);

  // Dodatkowe przekierowanie – gdy sesja została sprawdzona i użytkownik nie jest autoryzowany, a nie jest na stronie głównej.
  useEffect(() => {
    if (!isLoading && !isAuthenticated && pathname !== '/') {
      setAccessDenied(true);
      router.push('/');
    }
  }, [isLoading, isAuthenticated, pathname, router]);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, setIsAuthenticated, accessDenied, setAccessDenied, tokenExpired, setTokenExpired}}
    >
      {children}
    </AuthContext.Provider>
  );
};
