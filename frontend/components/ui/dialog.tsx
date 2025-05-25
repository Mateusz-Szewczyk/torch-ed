"use client"

import * as RadixDialog from "@radix-ui/react-dialog"
import type { ReactNode, ComponentPropsWithoutRef, ElementRef } from "react"
import { forwardRef } from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface DialogProps {
  children: ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
  defaultOpen?: boolean
  modal?: boolean
}

export const Dialog = ({ children, open, onOpenChange, defaultOpen, modal = true }: DialogProps) => {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange} defaultOpen={defaultOpen} modal={modal}>
      {children}
    </RadixDialog.Root>
  )
}

Dialog.displayName = "Dialog"

interface DialogTriggerProps extends ComponentPropsWithoutRef<typeof RadixDialog.Trigger> {
  children: ReactNode
  asChild?: boolean
}

export const DialogTrigger = forwardRef<
  ElementRef<typeof RadixDialog.Trigger>,
  DialogTriggerProps
>(({ children, asChild = false, className, ...props }, ref) => {
  return (
    <RadixDialog.Trigger ref={ref} asChild={asChild} className={className} {...props}>
      {children}
    </RadixDialog.Trigger>
  )
})

DialogTrigger.displayName = "DialogTrigger"

// POPRAWKA: Rozdziel typy dla Portal i Content
interface DialogPortalProps {
  children: ReactNode
  forceMount?: true // Portal akceptuje tylko true lub undefined
  container?: HTMLElement | null
}

export const DialogPortal = ({ children, forceMount, container }: DialogPortalProps) => {
  return (
    <RadixDialog.Portal forceMount={forceMount} container={container}>
      {children}
    </RadixDialog.Portal>
  )
}

DialogPortal.displayName = "DialogPortal"

interface DialogOverlayProps extends Omit<ComponentPropsWithoutRef<typeof RadixDialog.Overlay>, 'forceMount'> {
  className?: string
  forceMount?: boolean // Overlay może mieć boolean
}

export const DialogOverlay = forwardRef<
  ElementRef<typeof RadixDialog.Overlay>,
  DialogOverlayProps
>(({ className, forceMount, ...props }, ref) => (
  <RadixDialog.Overlay
    ref={ref}
    // POPRAWKA: Kondycjonalnie przekaż forceMount tylko jeśli true
    {...(forceMount === true && { forceMount: true })}
    className={cn(
      "fixed inset-0 z-50 bg-background/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
))

DialogOverlay.displayName = "DialogOverlay"

// POPRAWKA: Popraw typy dla DialogContent
interface DialogContentProps extends Omit<ComponentPropsWithoutRef<typeof RadixDialog.Content>, 'forceMount'> {
  children: ReactNode
  className?: string
  onInteractOutside?: (event: Event) => void
  onEscapeKeyDown?: (event: KeyboardEvent) => void
  onPointerDownOutside?: (event: Event) => void
  onFocusOutside?: (event: Event) => void
  forceMount?: boolean // Content może mieć boolean
}

export const DialogContent = forwardRef<
  ElementRef<typeof RadixDialog.Content>,
  DialogContentProps
>(({
  children,
  className,
  onInteractOutside,
  onEscapeKeyDown,
  onPointerDownOutside,
  onFocusOutside,
  forceMount,
  ...props
}, ref) => {
  return (
    <RadixDialog.Portal
      // POPRAWKA: Kondycjonalnie przekaż forceMount tylko jeśli true
      {...(forceMount === true && { forceMount: true })}
    >
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
        ref={ref}
        className={cn(
          "fixed left-[50%] top-[50%] z-50 translate-x-[-50%] translate-y-[-50%]",
          "w-[95vw] max-w-lg sm:max-w-xl md:max-w-2xl lg:max-w-4xl xl:max-w-5xl",
          "max-h-[90vh] overflow-hidden",
          "bg-background/95 backdrop-blur-md",
          "border border-border/30 dark:border-border/20",
          "shadow-[0_0_0_1px_rgba(0,0,0,0.05),0_10px_40px_-15px_rgba(0,0,0,0.25),0_2px_20px_-5px_rgba(0,0,0,0.1)]",
          "dark:shadow-[0_0_0_2px_rgba(255,255,255,0.05),0_10px_40px_-15px_rgba(0,0,0,0.5),0_2px_20px_-5px_rgba(0,0,0,0.3)]",
          "dark:bg-background/90 dark:backdrop-blur-md",
          "p-6 md:p-8",
          "rounded-xl",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
          "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          "data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%]",
          "data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]",
          "duration-200 ease-out",
          "focus:outline-none",
          className,
        )}
        onInteractOutside={onInteractOutside}
        onEscapeKeyDown={onEscapeKeyDown}
        onPointerDownOutside={onPointerDownOutside}
        onFocusOutside={onFocusOutside}
        // POPRAWKA: Kondycjonalnie przekaż forceMount tylko jeśli true
        {...(forceMount === true && { forceMount: true })}
        {...props}
      >
        {children}
        <RadixDialog.Close
          className={cn(
            "absolute right-5 top-5 z-10",
            "rounded-full p-2 opacity-70 transition-all",
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
})

DialogContent.displayName = "DialogContent"

interface DialogHeaderProps {
  children: ReactNode
  className?: string
}

export const DialogHeader = ({ children, className }: DialogHeaderProps) => {
  return (
    <div className={cn("flex flex-col space-y-2.5 text-center sm:text-left mb-6", className)}>
      {children}
    </div>
  )
}

DialogHeader.displayName = "DialogHeader"

interface DialogTitleProps extends ComponentPropsWithoutRef<typeof RadixDialog.Title> {
  children: ReactNode
  className?: string
}

export const DialogTitle = forwardRef<
  ElementRef<typeof RadixDialog.Title>,
  DialogTitleProps
>(({ children, className, ...props }, ref) => {
  return (
    <RadixDialog.Title
      ref={ref}
      className={cn(
        "text-xl font-semibold leading-none tracking-tight text-foreground mb-2",
        "sm:text-2xl",
        className
      )}
      {...props}
    >
      {children}
    </RadixDialog.Title>
  )
})

DialogTitle.displayName = "DialogTitle"

interface DialogDescriptionProps extends ComponentPropsWithoutRef<typeof RadixDialog.Description> {
  children: ReactNode
  className?: string
}

export const DialogDescription = forwardRef<
  ElementRef<typeof RadixDialog.Description>,
  DialogDescriptionProps
>(({ children, className, ...props }, ref) => {
  return (
    <RadixDialog.Description
      ref={ref}
      className={cn("text-sm text-muted-foreground mt-1.5", "leading-relaxed", className)}
      {...props}
    >
      {children}
    </RadixDialog.Description>
  )
})

DialogDescription.displayName = "DialogDescription"

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

DialogFooter.displayName = "DialogFooter"

interface DialogCloseProps extends ComponentPropsWithoutRef<typeof RadixDialog.Close> {
  children: ReactNode
  asChild?: boolean
  className?: string
}

export const DialogClose = forwardRef<
  ElementRef<typeof RadixDialog.Close>,
  DialogCloseProps
>(({ children, asChild = false, className, ...props }, ref) => {
  return (
    <RadixDialog.Close ref={ref} asChild={asChild} className={className} {...props}>
      {children}
    </RadixDialog.Close>
  )
})

DialogClose.displayName = "DialogClose"

// Additional utility components for better UX

interface DialogBodyProps {
  children: ReactNode
  className?: string
}

export const DialogBody = ({ children, className }: DialogBodyProps) => {
  return <div className={cn("overflow-y-auto flex-1 py-4", className)}>{children}</div>
}

DialogBody.displayName = "DialogBody"

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

DialogScrollArea.displayName = "DialogScrollArea"

// Backward compatibility exports
export {
  Dialog as DialogRoot,
  DialogTrigger as DialogButton,
  DialogContent as DialogWindow,
}

// Type exports for better TypeScript experience
export type {
  DialogProps,
  DialogTriggerProps,
  DialogContentProps,
  DialogPortalProps,
  DialogOverlayProps,
  DialogHeaderProps,
  DialogTitleProps,
  DialogDescriptionProps,
  DialogFooterProps,
  DialogCloseProps,
  DialogBodyProps,
  DialogScrollAreaProps,
}
