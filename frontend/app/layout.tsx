// app/layout.tsx
import './globals.css';
import { Inter } from 'next/font/google';
import { cookies } from 'next/headers';

import RootClient from '@/components/RootClient';

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = cookies();
  const languageCookie = cookieStore.get('language');
  const languageFromCookies = languageCookie?.value || 'en';

  return (
    <html lang={languageFromCookies}>
      <body className={inter.className}>
        <RootClient initialLanguage={languageFromCookies}>{children}</RootClient>
      </body>
    </html>
  );
}
