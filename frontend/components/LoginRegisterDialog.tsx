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
import { Eye, EyeOff, X, AlertCircle, CheckCircle, Info, ArrowLeft, Mail, Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface LoginRegisterDialogProps {
  children: React.ReactNode
  setIsAuthenticated: (val: boolean) => void
  autoOpen?: boolean
  initialView?: "auth" | "forgot-password" | "reset-password"
}

type ToastType = "success" | "error" | "info"
type View = "auth" | "forgot-password" | "reset-password"

interface Toast {
  message: string
  type: ToastType
}

interface PasswordRequirement {
  id: string
  label: string
  regex: RegExp
  met: boolean
}

const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/

// Enhanced password validation with individual requirements
const createPasswordRequirements = (): PasswordRequirement[] => [
  {
    id: 'length',
    label: 'Co najmniej 8 znaków',
    regex: /.{8,}/,
    met: false
  },
  {
    id: 'lowercase',
    label: 'Jedna mała litera (a-z)',
    regex: /[a-z]/,
    met: false
  },
  {
    id: 'uppercase',
    label: 'Jedna duża litera (A-Z)',
    regex: /[A-Z]/,
    met: false
  },
  {
    id: 'number',
    label: 'Jedna cyfra (0-9)',
    regex: /[0-9]/,
    met: false
  },
  {
    id: 'special',
    label: 'Jeden znak specjalny (!@#$%^&*)',
    regex: /[!@#$%^&*(),.?":{}|<>]/,
    met: false
  }
]

// Password Requirements Component
const PasswordRequirements = ({
  password,
  onValidityChange,
  show = true
}: {
  password: string
  onValidityChange: (isValid: boolean) => void
  show?: boolean
}) => {
  const [requirements, setRequirements] = useState<PasswordRequirement[]>(createPasswordRequirements())

  useEffect(() => {
    const updatedRequirements = requirements.map(req => ({
      ...req,
      met: req.regex.test(password)
    }))

    setRequirements(updatedRequirements)

    // Check if all requirements are met
    const allMet = updatedRequirements.every(req => req.met)
    onValidityChange(allMet)
  }, [password, onValidityChange, requirements])

  if (!show) return null

  return (
    <div className="mt-3 p-3 border border-border/50 rounded-lg bg-muted/30">
      <p className="text-sm font-medium text-muted-foreground mb-2">Wymagania hasła:</p>
      <ul className="space-y-1">
        {requirements.map((req) => (
          <li
            key={req.id}
            className={cn(
              "flex items-center text-xs transition-colors duration-200",
              req.met ? "text-green-600" : "text-muted-foreground"
            )}
          >
            <div className={cn(
              "w-4 h-4 rounded-full mr-2 flex items-center justify-center transition-colors duration-200",
              req.met ? "bg-green-500" : "bg-muted-foreground/20"
            )}>
              {req.met && <Check className="w-2.5 h-2.5 text-white" />}
            </div>
            {req.label}
          </li>
        ))}
      </ul>
    </div>
  )
}

// Email validation component
const EmailValidation = ({
  email,
  onValidityChange
}: {
  email: string
  onValidityChange: (isValid: boolean) => void
}) => {
  const [isValid, setIsValid] = useState<boolean | null>(null)

  useEffect(() => {
    if (!email) {
      setIsValid(null)
      onValidityChange(false)
      return
    }

    const valid = EMAIL_REGEX.test(email)
    setIsValid(valid)
    onValidityChange(valid)
  }, [email, onValidityChange])

  if (!email || isValid === null) return null

  return (
    <div className={cn(
      "flex items-center text-xs mt-1 transition-colors duration-200",
      isValid ? "text-green-600" : "text-orange-600"
    )}>
      {isValid ? (
        <>
          <CheckCircle className="h-3 w-3 mr-1" />
          Adres email jest prawidłowy
        </>
      ) : (
        <>
          <AlertCircle className="h-3 w-3 mr-1" />
          Podaj prawidłowy adres email
        </>
      )}
    </div>
  )
}

export function LoginRegisterDialog({
  children,
  setIsAuthenticated,
  autoOpen = false,
  initialView = "auth"
}: LoginRegisterDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [currentView, setCurrentView] = useState<View>(initialView)
  const [isStable, setIsStable] = useState(false)
  const [forceOpen, setForceOpen] = useState(false)

  const { t } = useTranslation()
  const router = useRouter()

  // Toast notification state
  const [toast, setToast] = useState<Toast | null>(null)

  // Login fields
  const [loginEmail, setLoginEmail] = useState("")
  const [loginPassword, setLoginPassword] = useState("")
  const [showLoginPassword, setShowLoginPassword] = useState(false)

  // Register fields
  const [registerEmail, setRegisterEmail] = useState("")
  const [registerPassword, setRegisterPassword] = useState("")
  const [registerPassword2, setRegisterPassword2] = useState("")
  const [showRegisterPassword, setShowRegisterPassword] = useState(false)
  const [showRegisterPassword2, setShowRegisterPassword2] = useState(false)

  // Forgot password fields
  const [forgotEmail, setForgotEmail] = useState("")
  const [isLoadingForgot, setIsLoadingForgot] = useState(false)

  // Reset password fields
  const [resetToken, setResetToken] = useState("")
  const [resetPassword, setResetPassword] = useState("")
  const [resetConfirmPassword, setResetConfirmPassword] = useState("")
  const [showResetPassword, setShowResetPassword] = useState(false)
  const [showResetConfirmPassword, setShowResetConfirmPassword] = useState(false)
  const [isLoadingReset, setIsLoadingReset] = useState(false)

  // Enhanced validation states
  const [registerEmailValid, setRegisterEmailValid] = useState(false)
  const [registerPasswordValid, setRegisterPasswordValid] = useState(false)
  const [registerPasswordsMatch, setRegisterPasswordsMatch] = useState(false)
  const [forgotEmailValid, setForgotEmailValid] = useState(false)
  const [resetPasswordValid, setResetPasswordValid] = useState(false)
  const [resetPasswordsMatch, setResetPasswordsMatch] = useState(false)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_FLASK_URL || "http://localhost:14440/api/v1"

  // Stabilizacja po mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsStable(true)
      if (autoOpen || initialView === "reset-password") {
        setIsOpen(true)
        setForceOpen(true)
      }
    }, 150)
    return () => clearTimeout(timer)
  }, [autoOpen, initialView])

  // Handle token from URL for reset password
  useEffect(() => {
    if (isStable && typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search)
      const token = urlParams.get('token')

      if (token && !resetToken) {
        setResetToken(token)
        setCurrentView("reset-password")
        setIsOpen(true)
        setForceOpen(true)
        const newUrl = window.location.pathname
        window.history.replaceState({}, document.title, newUrl)
      }
    }
  }, [isStable, resetToken])

  // Password confirmation validation
  useEffect(() => {
    if (registerPassword && registerPassword2) {
      setRegisterPasswordsMatch(registerPassword === registerPassword2)
    } else {
      setRegisterPasswordsMatch(false)
    }
  }, [registerPassword, registerPassword2])

  useEffect(() => {
    if (resetPassword && resetConfirmPassword) {
      setResetPasswordsMatch(resetPassword === resetConfirmPassword)
    } else {
      setResetPasswordsMatch(false)
    }
  }, [resetPassword, resetConfirmPassword])

  // Controlled dialog handler
  const handleOpenChange = useCallback((open: boolean) => {
    if (!isStable) return
    if (!open && forceOpen && currentView === "reset-password") return
    if (!open && currentView === "reset-password") return

    setIsOpen(open)
    if (!open) {
      setForceOpen(false)
    }
  }, [isStable, forceOpen, currentView])

  // Reset form when view changes
  useEffect(() => {
    if (currentView === "auth") {
      setForgotEmail("")
      setResetToken("")
      setResetPassword("")
      setResetConfirmPassword("")
      setForceOpen(false)
    }
  }, [currentView])

  // Clear toast after 8 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 8000)
      return () => clearTimeout(timer)
    }
  }, [toast])

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
        if (response.status === 423) {
          showToast(
            errData.message || "Twoje konto nie zostało potwierdzone. Sprawdź swój e-mail.",
            "error",
          )
          return
        }
        throw new Error(errData.error || "Failed to login")
      }

      const data = await response.json()
      const { is_confirmed, message } = data

      if (!is_confirmed) {
        showToast(
          message || "Twoje konto nie zostało potwierdzone. Sprawdź swój e-mail.",
          "error",
        )
      } else {
        showToast(message || "Zalogowano pomyślnie", "success")
      }

      setIsOpen(false)
      setIsAuthenticated(true)
      router.push("/")
    } catch (err) {
      console.error("Error logging in:", err)
      showToast("Nie udało się zalogować, sprawdź podane informacje!", "error")
    }
  }

  // Handle registration
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!registerEmailValid) {
      showToast("Podaj poprawny adres email", "error")
      return
    }

    if (!registerPasswordValid) {
      showToast("Hasło nie spełnia wszystkich wymagań", "error")
      return
    }

    if (!registerPasswordsMatch) {
      showToast("Hasła nie są identyczne", "error")
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

      showToast("Zarejestrowano pomyślnie. Sprawdź swój e-mail, aby potwierdzić rejestrację.", "success")

      setRegisterEmail("")
      setRegisterPassword("")
      setRegisterPassword2("")

      const loginTab = document.querySelector('[data-value="login"]') as HTMLElement
      if (loginTab) loginTab.click()
    } catch (err) {
      console.error("Error registering:", err)
      showToast("Nie udało się zarejestrować: " + String(err), "error")
    }
  }

  // Handle forgot password
  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!forgotEmailValid) {
      showToast("Podaj poprawny adres email", "error")
      return
    }

    setIsLoadingForgot(true)

    try {
      const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: forgotEmail }),
      })

      const data = await response.json()

      if (response.ok) {
        showToast(
          data.message || "Jeśli podany email istnieje w naszej bazie, wysłaliśmy link do resetowania hasła.",
          "success"
        )
        setCurrentView("auth")
      } else {
        throw new Error(data.error || "Failed to send reset email")
      }
    } catch (err) {
      console.error("Error sending reset email:", err)
      showToast("Wystąpił błąd. Spróbuj ponownie później.", "error")
    } finally {
      setIsLoadingForgot(false)
    }
  }

  // Handle reset password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!resetPasswordValid) {
      showToast("Hasło nie spełnia wszystkich wymagań", "error")
      return
    }

    if (!resetPasswordsMatch) {
      showToast("Hasła nie są identyczne", "error")
      return
    }

    setIsLoadingReset(true)

    try {
      const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: resetToken,
          new_password: resetPassword,
          confirm_password: resetConfirmPassword,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        showToast(
          data.message || "Hasło zostało pomyślnie zmienione. Możesz się teraz zalogować.",
          "success"
        )

        setTimeout(() => {
          setCurrentView("auth")
          setResetToken("")
          setResetPassword("")
          setResetConfirmPassword("")
          setForceOpen(false)
        }, 2000)
      } else {
        throw new Error(data.error || "Failed to reset password")
      }
    } catch (err) {
      console.error("Error resetting password:", err)
      showToast(String(err).replace("Error: ", ""), "error")
    } finally {
      setIsLoadingReset(false)
    }
  }

  const renderDialogTitle = () => {
    switch (currentView) {
      case "forgot-password":
        return "Resetowanie hasła"
      case "reset-password":
        return "Nowe hasło"
      default:
        return t("login_register_dialog.title", "Logowanie / Rejestracja")
    }
  }

  if (!isStable) {
    return null
  }

  return (
    <>
      <Dialog
        open={isOpen}
        onOpenChange={handleOpenChange}
        modal={true}
      >
        <DialogTrigger asChild>{children}</DialogTrigger>
        <DialogContent
          className="sm:max-w-2xl bg-background text-foreground max-h-[90vh] overflow-y-auto"
          aria-labelledby="auth-dialog-title"
          onPointerDownOutside={(e) => {
            if (forceOpen && currentView === "reset-password") {
              e.preventDefault()
            }
          }}
          onEscapeKeyDown={(e) => {
            if (forceOpen && currentView === "reset-password") {
              e.preventDefault()
            }
          }}
          onInteractOutside={(e) => {
            if (forceOpen && currentView === "reset-password") {
              e.preventDefault()
            }
          }}
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {currentView !== "auth" && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setCurrentView("auth")
                    setForceOpen(false)
                  }}
                  className="p-1 h-auto"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              )}
              {renderDialogTitle()}
            </DialogTitle>
          </DialogHeader>

          {/* Toast notification */}
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

          {/* Auth View (Login/Register) */}
          {currentView === "auth" && (
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="login" data-value="login">
                  Logowanie
                </TabsTrigger>
                <TabsTrigger value="register" data-value="register">
                  Rejestracja
                </TabsTrigger>
              </TabsList>

              {/* LOGIN TAB */}
              <TabsContent value="login">
                <form onSubmit={handleLogin}>
                  <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                      <Label htmlFor="login-email">Email</Label>
                      <Input
                        id="login-email"
                        type="email"
                        placeholder="Podaj swój adres email"
                        required
                        value={loginEmail}
                        onChange={(e) => setLoginEmail(e.target.value)}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="login-password">Hasło</Label>
                      <div className="relative">
                        <Input
                          id="login-password"
                          type={showLoginPassword ? "text" : "password"}
                          required
                          value={loginPassword}
                          onChange={(e) => setLoginPassword(e.target.value)}
                          placeholder="Minimum 8 znaków"
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

                  <div className="flex flex-col gap-3">
                    <Button type="submit" className="w-full">
                      Zaloguj się
                    </Button>

                    <Button
                      type="button"
                      variant="link"
                      className="text-sm text-muted-foreground p-0 h-auto"
                      onClick={() => setCurrentView("forgot-password")}
                    >
                      Zapomniałeś hasła?
                    </Button>
                  </div>
                </form>
              </TabsContent>

              {/* REGISTER TAB */}
              <TabsContent value="register">
                <form onSubmit={handleRegister}>
                  <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                      <Label htmlFor="register-email">Email</Label>
                      <Input
                        id="register-email"
                        type="email"
                        placeholder="Podaj swój adres email"
                        required
                        value={registerEmail}
                        onChange={(e) => setRegisterEmail(e.target.value)}
                        className={cn(
                          registerEmail && (registerEmailValid ? "border-green-500" : "border-orange-500")
                        )}
                      />
                      <EmailValidation
                        email={registerEmail}
                        onValidityChange={setRegisterEmailValid}
                      />
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="register-password">Hasło</Label>
                      <div className="relative">
                        <Input
                          id="register-password"
                          type={showRegisterPassword ? "text" : "password"}
                          required
                          value={registerPassword}
                          onChange={(e) => setRegisterPassword(e.target.value)}
                          placeholder="Minimum 8 znaków"
                          className={cn(
                            registerPassword && (registerPasswordValid ? "border-green-500" : "border-orange-500")
                          )}
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
                      <PasswordRequirements
                        password={registerPassword}
                        onValidityChange={setRegisterPasswordValid}
                        show={registerPassword.length > 0}
                      />
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="register-confirm-password">Potwierdź hasło</Label>
                      <div className="relative">
                        <Input
                          id="register-confirm-password"
                          type={showRegisterPassword2 ? "text" : "password"}
                          required
                          value={registerPassword2}
                          onChange={(e) => setRegisterPassword2(e.target.value)}
                          placeholder="Powtórz hasło"
                          className={cn(
                            registerPassword2 && (registerPasswordsMatch ? "border-green-500" : "border-orange-500")
                          )}
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
                      {registerPassword2 && (
                        <div className={cn(
                          "flex items-center text-xs mt-1",
                          registerPasswordsMatch ? "text-green-600" : "text-orange-600"
                        )}>
                          {registerPasswordsMatch ? (
                            <>
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Hasła są identyczne
                            </>
                          ) : (
                            <>
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Hasła nie są identyczne
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className="w-full"
                    disabled={!registerEmailValid || !registerPasswordValid || !registerPasswordsMatch}
                  >
                    Zarejestruj się
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          )}

          {/* Forgot Password View */}
          {currentView === "forgot-password" && (
            <form onSubmit={handleForgotPassword}>
              <div className="grid gap-4 py-4">
                <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <Mail className="h-5 w-5 text-blue-600" />
                  <div className="text-sm text-blue-800">
                    <p className="font-medium">Zresetujemy Twoje hasło</p>
                    <p>Podaj adres email, a wyślemy Ci link do resetowania hasła.</p>
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="forgot-email">Adres email</Label>
                  <Input
                    id="forgot-email"
                    type="email"
                    placeholder="Podaj swój adres email"
                    required
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    className={cn(
                      forgotEmail && (forgotEmailValid ? "border-green-500" : "border-orange-500")
                    )}
                  />
                  <EmailValidation
                    email={forgotEmail}
                    onValidityChange={setForgotEmailValid}
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoadingForgot || !forgotEmailValid}
              >
                {isLoadingForgot ? "Wysyłanie..." : "Wyślij link resetowania"}
              </Button>
            </form>
          )}

          {/* Reset Password View */}
          {currentView === "reset-password" && (
            <form onSubmit={handleResetPassword}>
              <div className="grid gap-4 py-4">
                <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <div className="text-sm text-green-800">
                    <p className="font-medium">Link jest prawidłowy</p>
                    <p>Ustaw nowe hasło dla swojego konta.</p>
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="reset-password">Nowe hasło</Label>
                  <div className="relative">
                    <Input
                      id="reset-password"
                      type={showResetPassword ? "text" : "password"}
                      required
                      value={resetPassword}
                      onChange={(e) => setResetPassword(e.target.value)}
                      placeholder="Minimum 8 znaków"
                      className={cn(
                        resetPassword && (resetPasswordValid ? "border-green-500" : "border-orange-500")
                      )}
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      onClick={() => setShowResetPassword(!showResetPassword)}
                      aria-label={showResetPassword ? "Hide password" : "Show password"}
                    >
                      {showResetPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <PasswordRequirements
                    password={resetPassword}
                    onValidityChange={setResetPasswordValid}
                    show={resetPassword.length > 0}
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="reset-confirm-password">Potwierdź nowe hasło</Label>
                  <div className="relative">
                    <Input
                      id="reset-confirm-password"
                      type={showResetConfirmPassword ? "text" : "password"}
                      required
                      value={resetConfirmPassword}
                      onChange={(e) => setResetConfirmPassword(e.target.value)}
                      placeholder="Powtórz hasło"
                      className={cn(
                        resetConfirmPassword && (resetPasswordsMatch ? "border-green-500" : "border-orange-500")
                      )}
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      onClick={() => setShowResetConfirmPassword(!showResetConfirmPassword)}
                      aria-label={showResetConfirmPassword ? "Hide password" : "Show password"}
                    >
                      {showResetConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {resetConfirmPassword && (
                    <div className={cn(
                      "flex items-center text-xs mt-1",
                      resetPasswordsMatch ? "text-green-600" : "text-orange-600"
                    )}>
                      {resetPasswordsMatch ? (
                        <>
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Hasła są identyczne
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-3 w-3 mr-1" />
                          Hasła nie są identyczne
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoadingReset || !resetPasswordValid || !resetPasswordsMatch}
              >
                {isLoadingReset ? "Resetowanie..." : "Ustaw nowe hasło"}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}

export default LoginRegisterDialog
