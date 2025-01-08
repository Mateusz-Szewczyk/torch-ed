// src/components/LanguageProvider.tsx

'use client';

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Cookies from 'js-cookie';

const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { i18n } = useTranslation();
  const [language, setLanguage] = useState('en');

  useEffect(() => {
    // Odczytaj ciasteczko języka
    const savedLanguage = Cookies.get('language') || 'en';
    setLanguage(savedLanguage);
    i18n.changeLanguage(savedLanguage);
  }, [i18n]);

  return (
    <>
      <script
        dangerouslySetInnerHTML={{
          __html: `
            document.documentElement.lang = "${language}";
          `,
        }}
      />
      {children}
    </>
  );
};

export default LanguageProvider;
