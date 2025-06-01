'use client'

import './globals.css'
import { Inter } from 'next/font/google'
import { ThemeProvider } from 'next-themes'
import RootClient from '@/components/RootClient'
import { ConversationProvider } from "@/contexts/ConversationContext"
import { AuthProvider } from "@/contexts/AuthContext"
import Script from 'next/script'
import { Toaster } from 'sonner'

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
      <meta name="description"
            content="Skuteczna nauka online z AI: automatycznie generowane egzaminy i fiszki SM-2,
            śledzenie postępów na interaktywnych wykresach oraz efektywna edukacja poparta badaniami."/>
      <meta name="google-site-verification" content="A-k-ozIAsnIHURo5Ag1Xfcx6QZJ8Pipzhb1LOEvxujw"/>
      <title>Torch-ed</title>
    </head>

    <body className={inter.className}>
    <AuthProvider>
      <ConversationProvider>
      <ThemeProvider
            attribute="class"
            enableSystem={true}
            defaultTheme="light"
            >
              <RootClient>
                <Toaster />
                {children}
              </RootClient>
            </ThemeProvider>
          </ConversationProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
