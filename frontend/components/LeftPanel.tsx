// components/LeftPanel.tsx

'use client'

import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { BookOpen, ChevronLeft, ChevronRight, UserCircle, Settings } from 'lucide-react'
import Link from 'next/link'
import { LoginRegisterDialog } from "@/components/LoginRegisterDialog"
import { SettingsDialog } from "@/components/SettingsDialog"
import { useTheme } from '@/contexts/ThemeContext'
import ManageFileDialog from '@/components/ManageFileDialog' // Import the new component

export function LeftPanel() {
  const [isPanelVisible, setIsPanelVisible] = useState(true)
  const { theme } = useTheme()

  // Zakładam, że masz dostęp do user_id, np. z kontekstu użytkownika
  const userId = 'user-123' // Przykładowe ID, zastąp rzeczywistym

  return (
    <div className={`bg-card text-foreground border-r border-border transition-all duration-300 ${isPanelVisible ? 'w-64' : 'w-20'} flex flex-col`}>
      <div className="p-4 flex-grow">
        <h2 className={`text-xl font-semibold mb-4 ${isPanelVisible ? '' : 'sr-only'}`}>Menu</h2>
        <div className="space-y-4">
          {/* Use ManageFileDialog component */}
          <ManageFileDialog userId={userId} isPanelVisible={isPanelVisible} />

          <Button asChild variant="outline" className="w-full justify-start">
            <Link href="/flashcards">
              <BookOpen className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">Flashcards</span>}
            </Link>
          </Button>
          <Button asChild variant="outline" className="w-full justify-start">
            <Link href="/">
              <span className="ml-2">Chat</span>
            </Link>
          </Button>
        </div>
      </div>
      <div className="p-4 border-t border-border">
        <div className="space-y-2">
          <LoginRegisterDialog>
            <Button variant="outline" className="w-full justify-start">
              <UserCircle className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">Login / Register</span>}
            </Button>
          </LoginRegisterDialog>
          <SettingsDialog>
            <Button variant="outline" className="w-full justify-start">
              <Settings className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">Settings</span>}
            </Button>
          </SettingsDialog>
        </div>
      </div>
      <Button
        variant="ghost"
        className="self-end mb-4 mr-2"
        onClick={() => setIsPanelVisible(!isPanelVisible)}
        aria-label={isPanelVisible ? "Hide panel" : "Show panel"}
      >
        {isPanelVisible ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </Button>
    </div>
  )
}
