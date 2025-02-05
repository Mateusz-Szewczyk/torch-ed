'use client'

import './globals.css'
import { Inter } from 'next/font/google'
import { ThemeProvider } from 'next-themes'
import RootClient from '@/components/RootClient'
import { ConversationProvider } from "@/contexts/ConversationContext"
import { AuthProvider } from "@/contexts/AuthContext"
import Script from 'next/script'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Pobieramy zmienną środowiskową
  const GTAG_ID = process.env.NEXT_PUBLIC_G_TAG || ''

  return (
    <html lang="en">
      <head>
        {/* Wstawiamy skrypt gtag.js z ID pobranym ze zmiennej */}
        <Script
          src={`https://www.googletagmanager.com/gtag/js?id=${GTAG_ID}`}
          strategy="afterInteractive"
        />
        <Script id="ga4-setup" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', '${GTAG_ID}');
          `}
        </Script>
      </head>

      <body className={inter.className}>
        <AuthProvider>
          <ConversationProvider>
            <ThemeProvider
              attribute="class"
              enableSystem={true}
              defaultTheme="light"
            >
              <RootClient>{children}</RootClient>
            </ThemeProvider>
          </ConversationProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
