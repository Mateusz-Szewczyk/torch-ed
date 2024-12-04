'use client';

import React, { useEffect, useState } from 'react';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/utils/i18n';
import { ThemeProvider } from 'next-themes';

interface ClientProviderProps {
  children: React.ReactNode;
  initialLanguage: string;
}

const ClientProvider: React.FC<ClientProviderProps> = ({ children, initialLanguage }) => {
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    if (i18n.language !== initialLanguage) {
      i18n.changeLanguage(initialLanguage).then(() => {
        setIsInitialized(true); // Ustawienie stanu po zmianie języka
      });
    } else {
      setIsInitialized(true); // Język już jest ustawiony
    }
  }, [initialLanguage]);

  if (!isInitialized) {
    return null; // Opcjonalnie: możesz dodać spinner ładowania
  }

  return (
    <ThemeProvider attribute="class">
      <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
    </ThemeProvider>
  );
};

export default ClientProvider;
