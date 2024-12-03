// components/ui/textarea.tsx

'use client'

import React from 'react'
import { cn } from '@/lib/utils' // Zakładam, że masz tę funkcję pomocniczą

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant?: 'default' | 'ghost'
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          // Base styles
          'w-full p-2 rounded-md border transition-colors duration-200',

          // Default variant styles
          variant === 'default' && [
            'bg-background text-foreground',
            'border-input',
            'placeholder:text-muted-foreground',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent'
          ],

          // Ghost variant styles
          variant === 'ghost' && [
            'bg-transparent border-transparent',
            'hover:bg-accent hover:border-border',
            'focus:bg-accent focus:border-border focus:ring-2 focus:ring-ring'
          ],

          // Additional custom classes
          className
        )}
        {...props}
      />
    )
  }
)

Textarea.displayName = 'Textarea'