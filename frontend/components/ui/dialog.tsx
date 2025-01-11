// components/ui/dialog.tsx

'use client';

import * as RadixDialog from '@radix-ui/react-dialog';
import { ReactNode } from 'react';
import { cn } from "@/lib/utils"; // Upewnij się, że masz tę funkcję

interface DialogProps {
  children: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export const Dialog = ({ children, open, onOpenChange }: DialogProps) => {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      {children}
    </RadixDialog.Root>
  );
};

interface DialogTriggerProps {
  children: ReactNode;
  className?: string;
}

export const DialogTrigger = ({ children}: DialogTriggerProps) => {
  return (
    <RadixDialog.Trigger asChild>
      {children}
    </RadixDialog.Trigger>
  );
};

interface DialogContentProps {
  children: ReactNode;
  className?: string;
}

export const DialogContent = ({ children, className }: DialogContentProps) => {
  return (
    <RadixDialog.Portal>
      <RadixDialog.Overlay
        className={cn(
          "fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50" // Dodano z-50
        )}
      />
      <RadixDialog.Content
        className={cn(
          "fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2",
          "bg-background text-foreground",
          "dark:bg-background dark:text-foreground",
          "p-6 rounded-md w-96 max-w-full max-h-[85vh] overflow-y-auto",
          "shadow-lg",
          "z-[50]", // Dodano z-50
            "overflow-visible",
          className
        )}
      >
        {children}
        <RadixDialog.Close
          className={cn(
            "absolute top-2 right-2",
            "text-muted-foreground hover:text-foreground",
            "dark:text-muted-foreground dark:hover:text-foreground"
          )}
        >
          ×
        </RadixDialog.Close>
      </RadixDialog.Content>
    </RadixDialog.Portal>
  );
};

interface DialogHeaderProps {
  children: ReactNode;
  className?: string;
}

export const DialogHeader = ({ children, className }: DialogHeaderProps) => {
  return (
    <div className={cn("mb-4", className)}>
      {children}
    </div>
  );
};

interface DialogTitleProps {
  children: ReactNode;
  className?: string;
}

export const DialogTitle = ({ children, className }: DialogTitleProps) => {
  return (
    <RadixDialog.Title
      className={cn(
        "text-lg font-semibold",
        "text-foreground",
        "dark:text-foreground",
        className
      )}
    >
      {children}
    </RadixDialog.Title>
  );
};

interface DialogDescriptionProps {
  children: ReactNode;
  className?: string;
}

export const DialogDescription = ({ children, className }: DialogDescriptionProps) => {
  return (
    <RadixDialog.Description
      className={cn(
        "text-sm text-muted-foreground",
        "dark:text-muted-foreground",
        className
      )}
    >
      {children}
    </RadixDialog.Description>
  );
};

interface DialogFooterProps {
  children: ReactNode;
  className?: string;
}

export const DialogFooter = ({ children, className }: DialogFooterProps) => {
  return (
    <div className={cn("mt-4 flex justify-end space-x-2", className)}>
      {children}
    </div>
  );
};

interface DialogCloseProps {
  children: ReactNode;
  className?: string;
}

export const DialogClose = ({ children}: DialogCloseProps) => {
  return (
    <RadixDialog.Close asChild>
      {children}
    </RadixDialog.Close>
  );
};