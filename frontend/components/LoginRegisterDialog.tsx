"use client"

import type React from "react"
import { useState, useEffect, useCallback } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { useTranslation } from "react-i18next"
import { useRouter } from "next/navigation"
import { Eye, EyeOff, X, AlertCircle, CheckCircle, Info } from "lucide-react"
import { cn } from "@/lib/utils"

interface LoginRegisterDialogProps {
  children: React.ReactNode
  setIsAuthenticated: (val: boolean) => void // Callback to set logged-in state
}

// Toast notification types
type ToastType = "success" | "error" | "info"

interface Toast {
  message: string
  type: ToastType
}

// Validation patterns
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[0-9\W]).{8,}$/

export function LoginRegisterDialog({ children, setIsAuthenticated }: LoginRegisterDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const { t } = useTranslation()
  const router = useRouter()

  // Fields for login
  const [loginEmail, setLoginEmail] = useState("")
  const [loginPassword, setLoginPassword] = useState("")
  const [showLoginPassword, setShowLoginPassword] = useState(false)

  // Fields for registration
  const [registerEmail, setRegisterEmail] = useState("")
  const [registerPassword, setRegisterPassword] = useState("")
  const [registerPassword2, setRegisterPassword2] = useState("")
  const [showRegisterPassword, setShowRegisterPassword] = useState(false)
  const [showRegisterPassword2, setShowRegisterPassword2] = useState(false)

  // Validation states
  const [emailValid, setEmailValid] = useState<boolean | null>(null)
  const [passwordValid, setPasswordValid] = useState<boolean | null>(null)
  const [passwordsMatch, setPasswordsMatch] = useState<boolean | null>(null)

  // State for notifications - now just a single toast
  const [toast, setToast] = useState<Toast | null>(null)

  // API base URL
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_FLASK_URL || "http://localhost:14440/api/v1"

  // Email validation
  useEffect(() => {
    if (registerEmail) {
      setEmailValid(EMAIL_REGEX.test(registerEmail))
    } else {
      setEmailValid(null)
    }
  }, [registerEmail])

  // Password validation
  useEffect(() => {
    if (registerPassword) {
      setPasswordValid(PASSWORD_REGEX.test(registerPassword))
    } else {
      setPasswordValid(null)
    }
  }, [registerPassword])

  // Password matching validation
  useEffect(() => {
    if (registerPassword && registerPassword2) {
      setPasswordsMatch(registerPassword === registerPassword2)
    } else {
      setPasswordsMatch(null)
    }
  }, [registerPassword, registerPassword2])

  // Clear toast after 8 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 8000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  // Show toast notification
  const showToast = useCallback((message: string, type: ToastType = "info") => {
    setToast({ message, type })
  }, [])

  // Handle login
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
        // Check if response is HTTP 423
        if (response.status === 423) {
          showToast(
            errData.message ||
              t(
                "login_register_dialog.account_not_confirmed",
                "Twoje konto nie zostało potwierdzone. Sprawdź swój e-mail, aby potwierdzić rejestrację.",
              ),
            "error",
          )
          return
        }
        throw new Error(errData.error || "Failed to login")
      }

      const data = await response.json()
      const { is_confirmed, message } = data

      // Show message based on confirmation status
      if (!is_confirmed) {
        showToast(
          message ||
            t(
              "login_register_dialog.account_not_confirmed",
              "Twoje konto nie zostało potwierdzone. Sprawdź swój e-mail, aby potwierdzić rejestrację.",
            ),
          "error",
        )
        // Optional: Prevent login for unconfirmed users
        // return; // Uncomment to block unconfirmed users
      } else {
        showToast(message || t("login_register_dialog.login_success", "Zalogowano pomyślnie"), "success")
      }

      // Hide the dialog
      setIsOpen(false)

      // Mark user as authenticated
      setIsAuthenticated(true)

      // Redirect to home
      router.push("/")
    } catch (err) {
      console.error("Error logging in:", err)
      showToast(t("login_register_dialog.login_error", "Nie udało się zalogować, sprawdź podane informacje!"), "error")
    }
  }

  // Handle registration
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validate inputs before submission
    if (!emailValid) {
      showToast(t("login_register_dialog.invalid_email", "Podaj poprawny adres email"), "error")
      return
    }

    if (!passwordValid) {
      showToast(
        t(
          "login_register_dialog.invalid_password",
          "Hasło musi zawierać co najmniej 8 znaków, jedną małą literę i jedną cyfrę lub znak specjalny",
        ),
        "error",
      )
      return
    }

    if (!passwordsMatch) {
      showToast(t("login_register_dialog.passwords_dont_match", "Hasła nie są takie same!"), "error")
      return
    }

    try {
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

      // After successful registration
      await response.json()

      showToast(
        t(
          "login_register_dialog.register_success",
          "Zarejestrowano pomyślnie. Sprawdź swój e-mail, aby potwierdzić rejestrację.",
        ),
        "success",
      )

      // Reset form fields
      setRegisterEmail("")
      setRegisterPassword("")
      setRegisterPassword2("")

      // Switch to login tab
      const loginTab = document.querySelector('[data-value="login"]') as HTMLElement
      if (loginTab) loginTab.click()
    } catch (err) {
      console.error("Error registering:", err)
      showToast(t("login_register_dialog.register_error", "Nie udało się zarejestrować: ") + String(err), "error")
    }
  }

  // Render validation message
  const ValidationMessage = ({
    valid,
    message,
    showWhenValid = false,
  }: {
    valid: boolean | null
    message: string
    showWhenValid?: boolean
  }) => {
    if (valid === null) return null
    if (!valid || showWhenValid) {
      return (
        <p className={cn("text-xs mt-1 flex items-center", valid ? "text-green-500" : "text-red-500")}>
          {valid ? <CheckCircle className="h-3 w-3 mr-1" /> : <AlertCircle className="h-3 w-3 mr-1" />}
          {message}
        </p>
      )
    }
    return null
  }

  return (
    <>
      {/* Modal */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>{children}</DialogTrigger>
        <DialogContent className="sm:max-w-2xl bg-background text-foreground" aria-labelledby="auth-dialog-title">
          <DialogHeader>
            <DialogTitle>{t("login_register_dialog.title")}</DialogTitle>
          </DialogHeader>

          {/* Toast notification inside dialog - only one at a time */}
          {toast && (
            <div
              className={cn(
                "mb-4 px-4 py-3 rounded-md shadow-md flex items-center gap-2 animate-in fade-in duration-300",
                toast.type === "error" && "bg-destructive text-destructive-foreground",
                toast.type === "success" && "bg-green-600 text-white",
                toast.type === "info" && "bg-blue-600 text-white",
              )}
              role="alert"
            >
              <div className="flex-shrink-0">
                {toast.type === "error" && <AlertCircle className="h-5 w-5" />}
                {toast.type === "success" && <CheckCircle className="h-5 w-5" />}
                {toast.type === "info" && <Info className="h-5 w-5" />}
              </div>
              <div className="flex-1">{toast.message}</div>
              <button
                type="button"
                className="flex-shrink-0 text-sm opacity-70 hover:opacity-100 transition-opacity"
                onClick={() => setToast(null)}
                aria-label="Close notification"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login" data-value="login">
                {t("login_register_dialog.login")}
              </TabsTrigger>
              <TabsTrigger value="register" data-value="register">
                {t("login_register_dialog.register")}
              </TabsTrigger>
            </TabsList>

            {/* LOGIN TAB */}
            <TabsContent value="login">
              <form onSubmit={handleLogin}>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="login-email">{t("login_register_dialog.email")}</Label>
                    <Input
                      id="login-email"
                      type="email"
                      placeholder={t("login_register_dialog.email_placeholder", "Podaj email")}
                      required
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      aria-describedby="login-email-error"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="login-password">{t("login_register_dialog.password")}</Label>
                    <div className="relative">
                      <Input
                        id="login-password"
                        type={showLoginPassword ? "text" : "password"}
                        required
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        aria-describedby="login-password-error"
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                        onClick={() => setShowLoginPassword(!showLoginPassword)}
                        aria-label={showLoginPassword ? "Hide password" : "Show password"}
                      >
                        {showLoginPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
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
                      placeholder={t("login_register_dialog.email_placeholder", "Podaj email")}
                      required
                      value={registerEmail}
                      onChange={(e) => setRegisterEmail(e.target.value)}
                      className={cn(
                        emailValid === false && "border-red-500 focus-visible:ring-red-500",
                        emailValid === true && "border-green-500 focus-visible:ring-green-500",
                      )}
                      aria-describedby="register-email-error"
                    />
                    <ValidationMessage
                      valid={emailValid}
                      message={t("login_register_dialog.invalid_email", "Podaj poprawny adres email")}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="register-password">{t("login_register_dialog.password")}</Label>
                    <div className="relative">
                      <Input
                        id="register-password"
                        type={showRegisterPassword ? "text" : "password"}
                        required
                        value={registerPassword}
                        onChange={(e) => setRegisterPassword(e.target.value)}
                        className={cn(
                          passwordValid === false && "border-red-500 focus-visible:ring-red-500",
                          passwordValid === true && "border-green-500 focus-visible:ring-green-500",
                        )}
                        aria-describedby="register-password-error"
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                        onClick={() => setShowRegisterPassword(!showRegisterPassword)}
                        aria-label={showRegisterPassword ? "Hide password" : "Show password"}
                      >
                        {showRegisterPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    <ValidationMessage
                      valid={passwordValid}
                      message={t(
                        "login_register_dialog.password_requirements",
                        "Hasło musi zawierać co najmniej 8 znaków, jedną małą literę i jedną cyfrę lub znak specjalny",
                      )}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="confirm-password">{t("login_register_dialog.confirm_password")}</Label>
                    <div className="relative">
                      <Input
                        id="confirm-password"
                        type={showRegisterPassword2 ? "text" : "password"}
                        required
                        value={registerPassword2}
                        onChange={(e) => setRegisterPassword2(e.target.value)}
                        className={cn(
                          passwordsMatch === false && "border-red-500 focus-visible:ring-red-500",
                          passwordsMatch === true && "border-green-500 focus-visible:ring-green-500",
                        )}
                        aria-describedby="confirm-password-error"
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                        onClick={() => setShowRegisterPassword2(!showRegisterPassword2)}
                        aria-label={showRegisterPassword2 ? "Hide password" : "Show password"}
                      >
                        {showRegisterPassword2 ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    <ValidationMessage
                      valid={passwordsMatch}
                      message={t("login_register_dialog.passwords_dont_match", "Hasła nie są takie same!")}
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full" disabled={!emailValid || !passwordValid || !passwordsMatch}>
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
