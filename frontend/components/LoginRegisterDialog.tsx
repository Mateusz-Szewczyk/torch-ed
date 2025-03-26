"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { useTranslation } from "react-i18next"
import { useRouter } from "next/navigation"

interface LoginRegisterDialogProps {
  children: React.ReactNode
  setIsAuthenticated: (val: boolean) => void // Callback to set logged-in state
}

// Simple toast notification types
type ToastType = "success" | "error" | "info"

interface Toast {
  message: string
  type: ToastType
}

export function LoginRegisterDialog({ children, setIsAuthenticated }: LoginRegisterDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const { t } = useTranslation()
  const router = useRouter()

  // Fields for login
  const [loginEmail, setLoginEmail] = useState("")
  const [loginPassword, setLoginPassword] = useState("")

  // Fields for registration
  const [registerEmail, setRegisterEmail] = useState("")
  const [registerPassword, setRegisterPassword] = useState("")
  const [registerPassword2, setRegisterPassword2] = useState("")

  // State for notifications
  const [toast, setToast] = useState<Toast | null>(null)

  // Clear toast after 20 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 20000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  // Pobierz bazowy URL API z zmiennej środowiskowej
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_FLASK_URL || "http://localhost:14440/api/v1"

  // Show toast notification
  const showToast = (message: string, type: ToastType = "info") => {
    setToast({ message, type })
  }

  // Handler: login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_name: loginEmail,
          password: loginPassword,
        }),
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.error || "Failed to login")
      }

      // Show success toast (outside modal)
      showToast("Zalogowano pomyślnie", "success")

      // Hide the dialog
      setIsOpen(false)

      // Mark user as authenticated
      setIsAuthenticated(true)

      // Redirect to home
      router.push("/")
    } catch (err) {
      console.error("Error logging in:", err)
      // Handle "User not confirmed" error
      if (String(err).includes("User not confirmed")) {
        showToast("Twoje konto nie zostało potwierdzone. Sprawdź swój e-mail, aby potwierdzić rejestrację.", "error")
      } else {
        showToast("Nie udało się zalogować, sprawdź podane informacje!", "error")
      }
    }
  }

  // Handler: register
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (registerPassword !== registerPassword2) {
        showToast("Hasła nie są takie same!", "error")
        return
      }

      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_name: registerEmail,
          password: registerPassword,
          password2: registerPassword2,
          email: registerEmail,
          age: 0,
          role: "user",
        }),
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.error || "Failed to register")
      }

      // Show success toast (outside modal)
      showToast("Rejestracja zakończona! Sprawdź swoją pocztę, aby potwierdzić konto.", "success")

      // Hide the dialog
      setIsOpen(false)
    } catch (err) {
      console.error("Error registering:", err)
      showToast("Nie udało się zarejestrować: " + String(err), "error")
    }
  }

  return (
    <>
      {/* Modal */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger>{children}</DialogTrigger>
        <DialogContent className="sm:max-w-[425px] bg-background text-foreground">
          <DialogHeader>
            <DialogTitle>{t("login_register_dialog.title")}</DialogTitle>
          </DialogHeader>
          {/* Error toast inside modal */}
          {isOpen && toast && toast.type === "error" && (
            <div className="mb-4 px-4 py-3 rounded-md shadow-lg bg-destructive text-destructive-foreground animate-fadeIn">
              <p>{toast.message}</p>
            </div>
          )}
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">{t("login_register_dialog.login")}</TabsTrigger>
              <TabsTrigger value="register">{t("login_register_dialog.register")}</TabsTrigger>
            </TabsList>

            {/* LOGIN TAB */}
            <TabsContent value="login">
              <form onSubmit={handleLogin}>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="email">{t("login_register_dialog.email")}</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="Podaj email"
                      required
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="password">{t("login_register_dialog.password")}</Label>
                    <Input
                      id="password"
                      type="password"
                      required
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full">
                  {t("login_register_dialog.login")}
                </Button>
              </form>
            </TabsContent>

            {/* REGISTER TAB */}
            <TabsContent value="register">
              <form onSubmit={handleRegister}>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="register-email">{t("login_register_dialog.email")}</Label>
                    <Input
                      id="register-email"
                      type="email"
                      placeholder="Podaj email"
                      required
                      value={registerEmail}
                      onChange={(e) => setRegisterEmail(e.target.value)}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="register-password">{t("login_register_dialog.password")}</Label>
                    <Input
                      id="register-password"
                      type="password"
                      required
                      value={registerPassword}
                      onChange={(e) => setRegisterPassword(e.target.value)}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="confirm-password">{t("login_register_dialog.confirm_password")}</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      required
                      value={registerPassword2}
                      onChange={(e) => setRegisterPassword2(e.target.value)}
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full">
                  {t("login_register_dialog.register")}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>


      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>
  )
}
