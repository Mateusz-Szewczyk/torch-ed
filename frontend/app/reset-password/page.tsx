// app/reset-password/page.tsx - POPRAWIONA WERSJA BEZ BŁĘDU REVALIDATE
"use client"

import { useEffect, useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { LoginRegisterDialog } from "@/components/LoginRegisterDialog"
import { Button } from "@/components/ui/button"
import { unstable_noStore as noStore } from 'next/cache'

// POPRAWKA: Usuń export const revalidate - powoduje konflikt
// POPRAWKA: Użyj tylko dynamic dla force-dynamic
export const dynamic = 'force-dynamic'

function ResetPasswordContent() {
  const [mounted, setMounted] = useState(false)
  const [hasToken, setHasToken] = useState(false)
  const [dialogKey, setDialogKey] = useState(0)
  const [isRedirecting, setIsRedirecting] = useState(false)
  const router = useRouter()
  const searchParams = useSearchParams()

  // Client-side only rendering
  useEffect(() => {
    setMounted(true)
  }, [])

  // Token validation and dialog setup
  useEffect(() => {
    if (mounted) {
      const token = searchParams.get('token')

      if (!token || token.length < 20) {
        console.log("No valid token found, redirecting to home")
        setIsRedirecting(true)

        const timeoutId = setTimeout(() => {
          router.push('/')
        }, 2000)

        return () => clearTimeout(timeoutId)
      } else {
        console.log("Valid token found:", token.substring(0, 10) + "...")
        setHasToken(true)
        setDialogKey(Date.now())
      }
    }
  }, [mounted, searchParams, router])

  // Prevent RSC interference
  useEffect(() => {
    if (hasToken) {
      const handleBeforeUnload = (e: BeforeUnloadEvent) => {
        e.preventDefault()
        e.returnValue = ''
      }

      const handlePopState = (e: PopStateEvent) => {
        e.preventDefault()
        window.history.pushState(null, '', window.location.href)
      }

      window.addEventListener('beforeunload', handleBeforeUnload)
      window.addEventListener('popstate', handlePopState)
      window.history.pushState(null, '', window.location.href)

      return () => {
        window.removeEventListener('beforeunload', handleBeforeUnload)
        window.removeEventListener('popstate', handlePopState)
      }
    }
  }, [hasToken])

  // Loading state
  if (!mounted) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p className="text-muted-foreground">Inicjalizacja...</p>
      </div>
    )
  }

  // Invalid token state
  if (isRedirecting || !hasToken) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-destructive mb-2">Link nieprawidłowy</h1>
          <p className="text-muted-foreground mb-4">
            Link do resetowania hasła jest nieprawidłowy lub wygasł.
          </p>
          <div className="flex items-center justify-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
            <span className="text-sm text-muted-foreground">Przekierowanie...</span>
          </div>
        </div>
      </div>
    )
  }

  // Main reset password form
  return (
    <div className="container mx-auto px-4 py-8 flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold mb-2">Resetowanie hasła</h1>
          <p className="text-sm text-muted-foreground">
            Ustaw nowe hasło dla swojego konta
          </p>
        </div>

        <LoginRegisterDialog
          key={dialogKey}
          setIsAuthenticated={() => {}}
          autoOpen={true}
          initialView="reset-password"
        >
          <Button className="w-full" size="lg">
            🔒 Ustaw nowe hasło
          </Button>
        </LoginRegisterDialog>

        <div className="mt-6 text-center">
          <p className="text-xs text-muted-foreground">
            Formularz otworzy się automatycznie
          </p>
        </div>
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  // POPRAWKA: Wywołaj noStore() na początku głównej funkcji
  noStore()

  return (
    <Suspense fallback={
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p className="text-muted-foreground">Ładowanie formularza resetowania...</p>
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  )
}
