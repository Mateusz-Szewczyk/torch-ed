// components/ui/dialog.tsx

'use client'

import * as RadixDialog from '@radix-ui/react-dialog'
import { ReactNode } from 'react'

interface DialogProps {
  children: ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export const Dialog = ({ children, open, onOpenChange }: DialogProps) => {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      {children}
    </RadixDialog.Root>
  )
}

interface DialogTriggerProps {
  children: ReactNode
}

export const DialogTrigger = ({ children }: DialogTriggerProps) => {
  return (
    <RadixDialog.Trigger asChild>
      {children}
    </RadixDialog.Trigger>
  )
}

interface DialogContentProps {
  children: ReactNode
}

export const DialogContent = ({ children }: DialogContentProps) => {
  return (
    <RadixDialog.Portal>
      <RadixDialog.Overlay className="fixed inset-0 bg-black bg-opacity-50" />
      <RadixDialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white p-6 rounded-md w-96 max-w-full max-h-[85vh] overflow-y-auto">
        {children}
        {/* Dodanie przycisku zamykającego dialog */}
        <RadixDialog.Close className="absolute top-2 right-2 text-gray-500 hover:text-gray-700">
          ×
        </RadixDialog.Close>
      </RadixDialog.Content>
    </RadixDialog.Portal>
  )
}

interface DialogHeaderProps {
  children: ReactNode
}

export const DialogHeader = ({ children }: DialogHeaderProps) => {
  return (
    <div className="mb-4">
      {children}
    </div>
  )
}

interface DialogTitleProps {
  children: ReactNode
}

export const DialogTitle = ({ children }: DialogTitleProps) => {
  return (
    <RadixDialog.Title className="text-lg font-semibold">
      {children}
    </RadixDialog.Title>
  )
}
