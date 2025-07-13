"use client"

import { useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { unstable_noStore as noStore } from "next/cache"

export const dynamic = "force-dynamic"

export default function ConfirmEmailPage() {
  noStore()
  const router       = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const token = searchParams.get("token")

    if (!token) {
      router.push("/")
      return
    }

    const backendBase =
      process.env.NEXT_PUBLIC_API_FLASK_URL ?? "http://localhost:14440/api/v1"

    // Docelowy endpoint: /auth/confirm_email/<token>
    const confirmUrl = `${backendBase}/auth/confirm_email/${token}`

    // Pełne przekierowanie (z zachowaniem cookies i 302 z backendu)
    window.location.replace(confirmUrl)
  }, [router, searchParams])

  // Prosty loader widoczny przez ułamek sekundy do czasu przekierowania
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      <p className="text-muted-foreground">Potwierdzanie konta…</p>
    </div>
  )
}
