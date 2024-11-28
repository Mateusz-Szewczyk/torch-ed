import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { LeftPanel } from '@/components/LeftPanel'
import { ThemeProvider } from '@/contexts/ThemeContext'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Chatbot with Flashcards',
  description: 'A minimalistic chatbot interface with flashcards functionality',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ThemeProvider>
          <div className="flex h-screen bg-background text-foreground">
            <LeftPanel />
            <main className="flex-1 overflow-auto">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  )
}

