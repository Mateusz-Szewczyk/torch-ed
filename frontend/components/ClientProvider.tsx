// components/ClientProvider.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../utils/i18n'; // Ensure the path to i18n is correct
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
        setIsInitialized(true); // Set state after changing the language
      });
    } else {
      setIsInitialized(true); // Language is already set
    }
  }, [initialLanguage]);

  if (!isInitialized) {
    return null; // Optionally: you can add a loading spinner here
  }

  return (
    <ThemeProvider attribute="class">
      <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
    </ThemeProvider>
  );
};

export default ClientProvider;
