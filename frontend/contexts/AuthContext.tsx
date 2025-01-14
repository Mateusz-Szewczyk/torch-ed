// src/context/AuthContext.tsx

'use client';

import React, { createContext, useState, useEffect, ReactNode } from 'react';

// Definicja typu dla kontekstu
interface AuthContextType {
  isAuthenticated: boolean;
  setIsAuthenticated: (auth: boolean) => void;
}

// Inicjalizacja kontekstu z domyślnymi wartościami
export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  setIsAuthenticated: () => {},
});

// Typ dla propsów AuthProvider
interface AuthProviderProps {
  children: ReactNode;
}

// Implementacja AuthProvider
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  useEffect(() => {
    // Sprawdzenie tokenu przy montowaniu komponentu
    const token = localStorage.getItem('token'); // Upewnij się, że klucz 'token' jest zgodny z implementacją logowania
    if (token) {
      setIsAuthenticated(true);
    } else {
      setIsAuthenticated(false);
    }

    // Nasłuchiwanie na zmiany w localStorage (np. logowanie/wylogowanie w innych zakładkach)
    const handleStorageChange = () => {
      const updatedToken = localStorage.getItem('token');
      setIsAuthenticated(!!updatedToken);
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, setIsAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};
