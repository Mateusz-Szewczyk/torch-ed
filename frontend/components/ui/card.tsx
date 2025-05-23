import * as React from "react"
import { cn } from "@/lib/utils"

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "group relative rounded-xl border bg-card/95 text-card-foreground backdrop-blur-sm flex flex-col",
      // Outer shadow - standard and hover states
      "shadow-[0_1px_3px_0_rgba(0,0,0,0.3),0_1px_2px_0_rgba(0,0,0,0.06)]",
      "dark:shadow-[0_1px_3px_0_rgba(0,0,0,0.3),0_1px_2px_0_rgba(0,0,0,0.2)]",
      "hover:shadow-[0_4px_6px_1px_rgba(0,0,0,0.1),0_2px_4px_-1px_rgba(0,0,0,0.06)]",
      "dark:hover:shadow-[0_4px_6px_1px_rgba(0,0,0,0.4),0_2px_4px_-1px_rgba(0,0,0,0.25)]",

      // Border styling
      "border-border/50 dark:border-border/30",
      "hover:border-border/80 dark:hover:border-border/50",

      // Default inner shadow - dark on light mode, light on dark mode
      "shadow-[inset_0_8px_12px_0_rgba(0,0,0,0.01)]",
      "dark:shadow-[inset_0_8px_12px_0_rgba(255,255,255,0.01)]",

      // Inverted inner shadow on hover - light on light mode, dark on dark mode
      "hover:shadow-[0_1px_3px_0_rgba(0,0,0,0.3),0_1px_2px_0_rgba(0,0,0,0.02),inset_0_8px_8px_0_rgba(255,255,255,0.1)]",
      "dark:hover:shadow-[0_4px_6px_-1px_rgba(0,0,0,0.4),0_2px_4px_-1px_rgba(0,0,0,0.02),inset_0_2px_12px_0_rgba(0,0,0,0.15)]",

      // Gradient overlay effect
      "before:absolute before:inset-0 before:rounded-xl before:bg-gradient-to-br before:from-white/5 before:to-transparent before:opacity-0 hover:before:opacity-100 before:transition-opacity before:duration-300",

      // Transitions and other utilities
      "transition-all duration-300 ease-out",
      "overflow-hidden",
      className,
    )}
    {...props}
  />
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex flex-col space-y-2 p-6 pb-4",
        "relative z-10",
        "border-b border-border/20 dark:border-border/10",
        className,
      )}
      {...props}
    />
  ),
)
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "text-xl sm:text-2xl font-semibold leading-tight tracking-tight",
        "text-card-foreground/90 dark:text-card-foreground/95",
        "group-hover:text-card-foreground transition-colors duration-200",
        className,
      )}
      {...props}
    />
  ),
)
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "text-sm sm:text-base text-muted-foreground/80 dark:text-muted-foreground/90 break-words leading-relaxed",
        "group-hover:text-muted-foreground transition-colors duration-200",
        className,
      )}
      {...props}
    />
  ),
)
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "p-6 pt-4 flex-grow relative z-10",
        "text-card-foreground/85 dark:text-card-foreground/90",
        className,
      )}
      {...props}
    />
  ),
)
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex items-center justify-between p-6 pt-4 gap-3",
        "relative z-10",
        "border-t border-border/20 dark:border-border/10",
        "bg-gradient-to-r from-transparent via-muted/20 to-transparent",
        className,
      )}
      {...props}
    />
  ),
)
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
