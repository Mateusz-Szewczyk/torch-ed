// components/ui/textarea.tsx

'use client'

import React from 'react'

interface TextareaProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  placeholder?: string
  className?: string
}

export const Textarea = ({ value, onChange, placeholder, className }: TextareaProps) => {
  return (
    <textarea
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`p-2 border rounded w-full ${className}`}
    />
  )
}
