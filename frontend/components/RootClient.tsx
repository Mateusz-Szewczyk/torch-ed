// components/RootClient.tsx
'use client';

import React, { useEffect, useState } from 'react';
import ClientProvider from '@/components/ClientProvider';
import ClientLayout from '@/components/ClientLayout';

const RootClient: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [initialLanguage, setInitialLanguage] = useState('en');

  useEffect(() => {
    // Get the 'language' cookie value
    const languageCookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith('language='))
      ?.split('=')[1];

    if (languageCookie) {
      setInitialLanguage(languageCookie);
    }
  }, []);

  return (
    <ClientProvider initialLanguage={initialLanguage}>
      <ClientLayout>{children}</ClientLayout>
    </ClientProvider>
  );
};

export default RootClient;
