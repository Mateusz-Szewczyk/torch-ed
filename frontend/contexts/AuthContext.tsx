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
  clearMessages: () => void; // Nowa funkcja do czyszczenia komunikatów
}

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  setIsAuthenticated: () => {},
  accessDenied: false,
  tokenExpired: false,
  setTokenExpired: () => {},
  setAccessDenied: () => {},
  clearMessages: () => {},
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

  // Funkcja do czyszczenia wszystkich komunikatów
  const clearMessages = useCallback(() => {
    setAccessDenied(false);
    setTokenExpired(false);
  }, []);

  // Funkcja opakowująca fetch używana do weryfikacji sesji
  const customFetch = useCallback(async (url: string, options?: RequestInit) => {
    return await fetch(url, { credentials: 'include', ...options });
  }, []);

  // Wrapper dla setIsAuthenticated - czyści komunikaty przy wylogowaniu
  const handleSetIsAuthenticated = useCallback((auth: boolean) => {
    setIsAuthenticated(auth);
    if (!auth) {
      // Gdy użytkownik zostaje wylogowany, wyczyść wszystkie komunikaty
      clearMessages();
    }
  }, [clearMessages]);

  // Sprawdzenie sesji przy montowaniu komponentu
  useEffect(() => {
    const checkSession = async () => {
      try {
        const API_BASE_URL =
          process.env.NEXT_PUBLIC_API_FLASK_URL ||
          'http://localhost:14440/api/v1';

        const authUrl = `${API_BASE_URL}/auth/session-check`;
        console.log('Session check URL:', authUrl);

        const res = await customFetch(authUrl);
        console.log('Session check status:', res.status);

        if (res.ok) {
          const data = await res.json();
          setIsAuthenticated(data.authenticated);
          console.log('User authenticated:', data.authenticated);
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

  // Wyczyść komunikaty przy zmianie route
  useEffect(() => {
    clearMessages();
  }, [pathname, clearMessages]);

  // Globalne przechwytywanie fetch
  useEffect(() => {
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const response = await originalFetch(...args);

      // Tylko jeśli user jest authenticated i dostaje 401, znaczy że token expired
      if (response.status === 401 && isAuthenticated && !isLoading) {
        console.warn('Received 401 – token expired, logging out.');
        setIsAuthenticated(false);
        // Pokaż komunikat tylko jeśli użytkownik był rzeczywiście zalogowany
        setTokenExpired(true);

        // Delay przekierowania żeby user zobaczył komunikat
        setTimeout(() => {
          router.push('/');
        }, 1000);
      }
      return response;
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, [isAuthenticated, isLoading, router]);

  // Przekierowanie dla nieautoryzowanych użytkowników
  useEffect(() => {
    // Tylko jeśli loading zakończony, user nie authenticated, nie jest na głównej
    // I nie wyświetlamy już komunikatu o tokenExpired (żeby nie dublować)
    if (!isLoading && !isAuthenticated && pathname !== '/' && !tokenExpired) {
      console.log('Access denied - redirecting to home');
      setAccessDenied(true);

      // Delay przekierowania żeby user zobaczył komunikat
      setTimeout(() => {
        router.push('/');
      }, 1000);
    }
  }, [isLoading, isAuthenticated, pathname, router, tokenExpired]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        setIsAuthenticated: handleSetIsAuthenticated,
        accessDenied,
        setAccessDenied,
        tokenExpired,
        setTokenExpired,
        clearMessages
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
