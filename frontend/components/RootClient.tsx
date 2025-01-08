// src/components/RootClient.tsx
'use client';

import React, { ReactNode, useState, useEffect } from 'react';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/utils/i18n'; // Upewnij się, że i18n jest poprawnie skonfigurowany
import ClientLayout from '@/components/ClientLayout';

interface RootClientProps {
  children: ReactNode;
}

const RootClient: React.FC<RootClientProps> = ({ children }) => {
  const [initialLanguage, setInitialLanguage] = useState('en');

  useEffect(() => {
    // Odczytanie wartości języka z ciasteczka
    const languageCookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith('language='))
      ?.split('=')[1];

    if (languageCookie) {
      setInitialLanguage(languageCookie);
    }
  }, []);

  useEffect(() => {
    // Zmiana języka w instancji i18n, jeśli jest inny niż aktualny
    if (initialLanguage !== i18n.language) {
      i18n.changeLanguage(initialLanguage).catch(err => {
        console.error('Failed to change language:', err);
      });
    }
  }, [initialLanguage]);

  return (
    <I18nextProvider i18n={i18n}>
      <ClientLayout>
        {children}
      </ClientLayout>
    </I18nextProvider>
  );
};

export default RootClient;
