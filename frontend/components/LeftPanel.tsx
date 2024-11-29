'use client'

import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { BookOpen, Upload, File, X, MessageSquare, ChevronLeft, ChevronRight, UserCircle, Settings } from 'lucide-react'
import Link from 'next/link'
import { LoginRegisterDialog } from "@/components/LoginRegisterDialog"
import { SettingsDialog } from "@/components/SettingsDialog"
import { useTheme } from '@/contexts/ThemeContext'

type UploadedFile = {
  id: string;
  name: string;
  size: number;
}

export function LeftPanel() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isPanelVisible, setIsPanelVisible] = useState(true)
  const { theme } = useTheme()

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      const newFiles = Array.from(files).map(file => ({
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: file.size
      }))
      setUploadedFiles(prev => [...prev, ...newFiles])
    }
  }

  const removeFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== id))
  }

  return (
    <div className={`bg-background text-foreground border-r border-border transition-all duration-300 ${isPanelVisible ? 'w-64' : 'w-16'} flex flex-col`}>
      <div className="p-4 flex-grow">
        <h2 className={`text-xl font-semibold mb-4 ${isPanelVisible ? '' : 'sr-only'}`}>Menu</h2>
        <div className="space-y-4">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" className="w-full justify-start">
                <File className="h-4 w-4" />
                {isPanelVisible && <span className="ml-2">Uploaded Files</span>}
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-background border-border">
              <DialogHeader>
                <DialogTitle className="text-foreground">Uploaded Files</DialogTitle>
              </DialogHeader>
              <ScrollArea className="h-[300px] w-full pr-4">
                {uploadedFiles.map(file => (
                  <div key={file.id} className="flex items-center justify-between py-2">
                    <span className="truncate text-foreground">{file.name}</span>
                    <Button variant="ghost" size="sm" onClick={() => removeFile(file.id)}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </ScrollArea>
              <Button asChild className="w-full mt-4">
                <label>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload New File
                  <input type="file" className="hidden" onChange={handleFileUpload} multiple />
                </label>
              </Button>
            </DialogContent>
          </Dialog>
          <Button asChild variant="outline" className="w-full justify-start">
            <Link href="/flashcards">
              <BookOpen className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">Flashcards</span>}
            </Link>
          </Button>
          <Button asChild variant="outline" className="w-full justify-start">
            <Link href="/">
              <MessageSquare className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">Chat</span>}
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

