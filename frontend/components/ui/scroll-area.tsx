// components/ScrollArea.tsx

"use client"

import * as React from "react"
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area"

import { cn } from "@/lib/utils"

const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>
>(({ className, children, ...props }, ref) => {
  const viewportRef = React.useRef<HTMLDivElement>(null)

  // Fix dla Radix UI ScrollArea overflow bug
  React.useEffect(() => {
    const viewport = viewportRef.current
    if (!viewport) return

    // Znajdź div z display: table który Radix automatycznie dodaje
    const tableDiv = viewport.querySelector('[style*="display: table"]') as HTMLElement
    if (tableDiv) {
      // Zastąp problematyczne style
      tableDiv.style.display = 'block'
      tableDiv.style.minWidth = 'auto'
      tableDiv.style.width = '100%'
      tableDiv.style.maxWidth = '100%'
      tableDiv.style.overflow = 'hidden'
      tableDiv.style.boxSizing = 'border-box'
    }

    // Obserwuj zmiany w DOM (gdy Radix dodaje nowe elementy)
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            const element = node as HTMLElement
            // Sprawdź czy nowy element ma problematyczne style
            if (element.style.display === 'table' && element.style.minWidth === '100%') {
              element.style.display = 'block'
              element.style.minWidth = 'auto'
              element.style.width = '100%'
              element.style.maxWidth = '100%'
              element.style.overflow = 'hidden'
              element.style.boxSizing = 'border-box'
            }
          }
        })
      })
    })

    observer.observe(viewport, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['style']
    })

    return () => {
      observer.disconnect()
    }
  }, [children])

  return (
    <ScrollAreaPrimitive.Root
      ref={ref}
      className={cn("relative overflow-hidden", className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        ref={viewportRef}
        className="w-full h-full rounded-[inherit] overflow-hidden"
        style={{
          // Force zawartość do pozostania w granicach
          maxWidth: '100%',
          boxSizing: 'border-box'
        }}
      >
        <div
          className="w-full h-full overflow-hidden"
          style={{
            maxWidth: '100%',
            boxSizing: 'border-box'
          }}
        >
          {children}
        </div>
      </ScrollAreaPrimitive.Viewport>
      <ScrollBar />
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
})
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName

const ScrollBar = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>
>(({ className, orientation = "vertical", ...props }, ref) => (
  <ScrollAreaPrimitive.ScrollAreaScrollbar
    ref={ref}
    orientation={orientation}
    className={cn(
      "flex touch-none select-none transition-colors",
      orientation === "vertical"
        ? "h-full w-2.5 border-l border-l-transparent p-[1px]"
        : "h-2.5 flex-col border-t border-t-transparent p-[1px]",
      className
    )}
    {...props}
  >
    <ScrollAreaPrimitive.ScrollAreaThumb className="relative flex-1 rounded-full bg-border" />
  </ScrollAreaPrimitive.ScrollAreaScrollbar>
))
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName

export { ScrollArea, ScrollBar }
