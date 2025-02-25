// src/components/ui/input.tsx
'use client'

import * as React from "react"
import TextareaAutosize from "react-textarea-autosize"
import { cn } from "@/lib/utils"

// Właściwości dla trybu jednoliniowego
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  multiline?: false
}

// Właściwości dla trybu wieloliniowego
export interface TextAreaProps
  extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, "style"> {
  multiline: true
  maxRows?: number
}

type CombinedProps = InputProps | TextAreaProps

const Input = React.forwardRef<HTMLInputElement | HTMLTextAreaElement, CombinedProps>(
  (props, ref) => {
    const { multiline = false, className, ...rest } = props

    // Lokalne refy do przekazania do <input> lub <TextareaAutosize>
    const inputRef = React.useRef<HTMLInputElement>(null)
    const textareaRef = React.useRef<HTMLTextAreaElement>(null)

    // Udostępniamy ref na zewnątrz
    React.useImperativeHandle(ref, () => {
      return multiline ? (textareaRef.current as HTMLTextAreaElement) : (inputRef.current as HTMLInputElement)
    })

    // Podstawowe klasy
    const commonClassNames = cn(
      "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background",
      "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className
    )

    if (multiline) {
      // Mamy do czynienia z wieloliniowym <textarea> z auto-rozszerzaniem
      const { maxRows = 10, ...textareaProps } = rest as TextAreaProps

      return (
        <TextareaAutosize
          ref={textareaRef}
          className={commonClassNames}
          maxRows={maxRows}
          minRows={1}
          {...textareaProps}
        />
      )
    }

    // Tryb jednoliniowy
    return (
      <input
        ref={inputRef}
        className={commonClassNames}
        {...(rest as React.InputHTMLAttributes<HTMLInputElement>)}
      />
    )
  }
)

Input.displayName = "Input"

export { Input }
