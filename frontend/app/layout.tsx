// layout.tsx

import './globals.css';
import { Inter } from 'next/font/google';
import ClientProvider from '@/components/ClientProvider';
import { cookies } from 'next/headers'; // Importujemy API ciasteczek Next.js
import ClientLayout from '@/components/ClientLayout'; // Importujemy nowy komponent

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // Pobieramy język z ciasteczek
  const cookieStore = cookies();
  const languageFromCookies = cookieStore.get('language')?.value || 'en';

  return (
    <html lang={languageFromCookies}>
      <body className={inter.className}>
        <ClientProvider initialLanguage={languageFromCookies}>
          <ClientLayout>{children}</ClientLayout>
        </ClientProvider>
      </body>
    </html>
  );
}
