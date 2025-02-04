// src/components/ui/input.tsx
'use client';

import * as React from "react";
import TextareaAutosize from "react-textarea-autosize";
import { cn } from "@/lib/utils";

// Definiujemy typ propsów jako union dla inputa i textarea
type InputProps = {
  label?: string;
  wrapperClassName?: string;
} & (
  | (React.InputHTMLAttributes<HTMLInputElement> & { multiline?: false })
  | (React.TextareaHTMLAttributes<HTMLTextAreaElement> & { multiline: true })
);

// Type guard – sprawdza, czy ref jest mutable
function isMutableRef<T>(ref: React.Ref<T>): ref is React.MutableRefObject<T | null> {
  return ref !== null && typeof ref === "object" && "current" in ref;
}

// Helper do łączenia refów
function mergeRefs<T>(...refs: React.Ref<T>[]): React.RefCallback<T> {
  return (value: T) => {
    refs.forEach(ref => {
      if (typeof ref === "function") {
        ref(value);
      } else if (ref && isMutableRef(ref)) {
        ref.current = value;
      }
    });
  };
}

const Input = React.forwardRef<HTMLInputElement | HTMLTextAreaElement, InputProps>(
  ({ label, wrapperClassName, multiline = false, className, id, ...props }, ref) => {
    // Wywołujemy useRef zawsze, niezależnie od trybu
    const textareaRef = React.useRef<HTMLTextAreaElement>(null);

    // useLayoutEffect wywoływany zawsze; wewnątrz sprawdzamy, czy multiline jest true
    React.useLayoutEffect(() => {
      if (multiline && textareaRef.current) {
        // Resetujemy wysokość, aby odczytać scrollHeight
        textareaRef.current.style.height = "auto";
        // Ustawiamy wysokość: minimum między scrollHeight a 25% wysokości okna
        const newHeight = Math.min(textareaRef.current.scrollHeight, window.innerHeight * 0.25);
        textareaRef.current.style.height = `${newHeight}px`;
      }
    }, [multiline, (props as React.TextareaHTMLAttributes<HTMLTextAreaElement>).value]);

    if (multiline) {
      const { style, ...rest } = props as React.TextareaHTMLAttributes<HTMLTextAreaElement>;
      return (
        <div className={cn("flex flex-col w-full", wrapperClassName)}>
          {label && (
            <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
              {label}
            </label>
          )}
          <TextareaAutosize
            id={id}
            className={cn(
              "w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
              className
            )}
            // Łączymy lokalny ref z przekazanym refem
            ref={mergeRefs(textareaRef, ref)}
            style={style as React.CSSProperties & { height?: number } | undefined}
            {...rest}
          />
        </div>
      );
    } else {
      return (
        <div className={cn("flex flex-col w-full", wrapperClassName)}>
          {label && (
            <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
              {label}
            </label>
          )}
          <input
            id={id}
            type={(props as React.InputHTMLAttributes<HTMLInputElement>).type}
            className={cn(
              "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
              className
            )}
            ref={ref as React.Ref<HTMLInputElement>}
            {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
          />
        </div>
      );
    }
  }
);

Input.displayName = "Input";

export { Input };
