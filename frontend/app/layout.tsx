import './globals.css';
import { Inter } from 'next/font/google';
import ClientProvider from '@/components/ClientProvider';
import { LeftPanel } from '@/components/LeftPanel';
import { cookies } from 'next/headers'; // Importujemy API ciasteczek Next.js

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // Pobieramy język z ciasteczek
  const cookieStore = cookies();
  const languageFromCookies = cookieStore.get('language')?.value || 'en';

  return (
    <html lang={languageFromCookies}>
      <body className={inter.className}>
        <ClientProvider initialLanguage={languageFromCookies}>
          <div className="flex h-screen bg-background text-foreground">
            <LeftPanel />
            <main className="flex-1 overflow-auto">{children}</main>
          </div>
        </ClientProvider>
      </body>
    </html>
  );
}
