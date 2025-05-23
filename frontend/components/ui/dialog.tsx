"use client"

import * as RadixDialog from "@radix-ui/react-dialog"
import type { ReactNode } from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

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
  asChild?: boolean
  className?: string
}

export const DialogTrigger = ({ children, asChild = false }: DialogTriggerProps) => {
  return <RadixDialog.Trigger asChild={asChild}>{children}</RadixDialog.Trigger>
}

interface DialogContentProps {
  children: ReactNode
  className?: string
  onInteractOutside?: (event: Event) => void
}

export const DialogContent = ({ children, className, onInteractOutside }: DialogContentProps) => {
  return (
    <RadixDialog.Portal>
      <RadixDialog.Overlay
        className={cn(
          "fixed inset-0 z-50",
          "bg-gradient-to-b from-black/60 to-black/70 backdrop-blur-[2px]",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
          "duration-300 ease-in-out",
        )}
      />
      <RadixDialog.Content
        className={cn(
          "fixed left-[50%] top-[50%] z-50 translate-x-[-50%] translate-y-[-50%]",
          "w-[95vw] max-w-lg sm:max-w-xl md:max-w-2xl lg:max-w-4xl xl:max-w-5xl",
          "max-h-[90vh] overflow-hidden",
          "bg-background/95 backdrop-blur-md",
          "border border-border/30 dark:border-border/20",
          "shadow-[0_0_0_1px_rgba(0,0,0,0.05),0_10px_40px_-15px_rgba(0,0,0,0.25),0_2px_20px_-5px_rgba(0,0,0,0.1)]",
          "dark:shadow-[0_0_0_2px_rgba(255,255,255,0.05),0_10px_40px_-15px_rgba(0,0,0,0.5),0_2px_20px_-5px_rgba(0,0,0,0.3)]",
          "dark:bg-background/90 dark:backdrop-blur-md",
          "p-6 md:p-8", // Increased padding
          "rounded-xl",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
          "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          "data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%]",
          "data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]",
          "duration-200 ease-out",
          className,
        )}
        onInteractOutside={onInteractOutside}
      >
        {children}
        <RadixDialog.Close
          className={cn(
            "absolute right-5 top-5 z-10", // Adjusted position
            "rounded-full p-2 opacity-70 transition-all", // Increased padding
            "text-foreground/70 dark:text-foreground/50",
            "hover:opacity-100 hover:bg-muted/80 hover:scale-105",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
            "disabled:pointer-events-none",
            "data-[state=open]:bg-accent/50 data-[state=open]:text-muted-foreground",
            "backdrop-blur-sm",
          )}
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </RadixDialog.Close>
      </RadixDialog.Content>
    </RadixDialog.Portal>
  )
}

interface DialogHeaderProps {
  children: ReactNode
  className?: string
}

export const DialogHeader = ({ children, className }: DialogHeaderProps) => {
  return <div className={cn("flex flex-col space-y-2.5 text-center sm:text-left mb-6", className)}>{children}</div>
}

interface DialogTitleProps {
  children: ReactNode
  className?: string
}

export const DialogTitle = ({ children, className }: DialogTitleProps) => {
  return (
    <RadixDialog.Title
      className={cn("text-xl font-semibold leading-none tracking-tight text-foreground mb-2", "sm:text-2xl", className)}
    >
      {children}
    </RadixDialog.Title>
  )
}

interface DialogDescriptionProps {
  children: ReactNode
  className?: string
}

export const DialogDescription = ({ children, className }: DialogDescriptionProps) => {
  return (
    <RadixDialog.Description className={cn("text-sm text-muted-foreground mt-1.5", "leading-relaxed", className)}>
      {children}
    </RadixDialog.Description>
  )
}

interface DialogFooterProps {
  children: ReactNode
  className?: string
}

export const DialogFooter = ({ children, className }: DialogFooterProps) => {
  return (
    <div
      className={cn(
        "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-3 gap-3 mt-8",
        "border-t border-border/10 pt-4 mt-8",
        className,
      )}
    >
      {children}
    </div>
  )
}

interface DialogCloseProps {
  children: ReactNode
  asChild?: boolean
  className?: string
}

export const DialogClose = ({ children, asChild = false, className }: DialogCloseProps) => {
  return (
    <RadixDialog.Close asChild={asChild} className={className}>
      {children}
    </RadixDialog.Close>
  )
}

// Additional utility components for better UX

interface DialogBodyProps {
  children: ReactNode
  className?: string
}

export const DialogBody = ({ children, className }: DialogBodyProps) => {
  return <div className={cn("overflow-y-auto flex-1 py-4", className)}>{children}</div>
}

interface DialogScrollAreaProps {
  children: ReactNode
  className?: string
  maxHeight?: string
}

export const DialogScrollArea = ({ children, className, maxHeight = "60vh" }: DialogScrollAreaProps) => {
  return (
    <div
      className={cn(
        "overflow-y-auto px-1 -mx-1 py-4",
        "scrollbar-thin scrollbar-thumb-rounded scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent",
        "hover:scrollbar-thumb-muted-foreground/30",
        className,
      )}
      style={{ maxHeight }}
    >
      {children}
    </div>
  )
}
