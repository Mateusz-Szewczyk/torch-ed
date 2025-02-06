// src/components/ui/textarea.tsx
'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant?: 'default' | 'ghost'
  label?: string
  id?: string
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant = 'default', label, id, ...props }, ref) => {
    return (
      <div className="flex flex-col">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={id}
          className={cn(
            // Podstawowe style
            'w-full p-2 rounded-md border transition-colors duration-200 text-sm',

            // Default variant
            variant === 'default' && [
              'bg-background text-foreground',
              'border-input',
              'placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent'
            ],

            // Ghost variant
            variant === 'ghost' && [
              'bg-transparent border-transparent',
              'hover:bg-accent hover:border-border',
              'focus:bg-accent focus:border-border focus:ring-2 focus:ring-ring'
            ],

            className
          )}
          {...props}
        />
      </div>
    )
  }
)

Textarea.displayName = 'Textarea'
