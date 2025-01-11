// app/layout.tsx

'use client'; // Oznacza, że ten komponent jest komponentem klienta

import './globals.css';
import { Inter } from 'next/font/google';
import { ThemeProvider } from 'next-themes';
import RootClient from '@/components/RootClient';
import { ConversationProvider } from "@/contexts/ConversationContext";

const inter = Inter({ subsets: ['latin'] });

function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
          <ConversationProvider>
            <ThemeProvider attribute="class" enableSystem={true} defaultTheme="light">
              <RootClient>{children}</RootClient>
            </ThemeProvider>
          </ConversationProvider>
      </body>
    </html>
  );
}

export default RootLayout;
