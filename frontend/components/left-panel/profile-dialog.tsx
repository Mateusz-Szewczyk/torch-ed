"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  User,
  Lock,
  Trash2,
  Eye,
  EyeOff,
  Mail,
  Calendar,
  AlertTriangle,
  Download,
  Settings,
  Check,
  Edit2,
  Loader2,
  CheckCircle,
  X,
  Info
} from "lucide-react"
import { cn } from "@/lib/utils"

interface ProfileDialogProps {
  isOpen: boolean
  onClose: () => void
  onLogout: () => void
  onUserUpdate?: (userData: UserData) => void
}

interface UserData {
  email: string
  username: string
  joinDate: string
  id: number
  role: string
  confirmed: boolean
}

interface PasswordChangeData {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

interface PasswordRequirement {
  id: string
  label: string
  regex: RegExp
  met: boolean
}

interface StatusMessage {
  type: 'success' | 'error' | 'info'
  message: string
  show: boolean
}

const createPasswordRequirements = (): PasswordRequirement[] => [
  {
    id: 'length',
    label: 'profile.password.requirements.length',
    regex: /.{8,}/,
    met: false
  },
  {
    id: 'lowercase',
    label: 'profile.password.requirements.lowercase',
    regex: /[a-z]/,
    met: false
  },
  {
    id: 'uppercase',
    label: 'profile.password.requirements.uppercase',
    regex: /[A-Z]/,
    met: false
  },
  {
    id: 'number',
    label: 'profile.password.requirements.number',
    regex: /[0-9]/,
    met: false
  },
  {
    id: 'special',
    label: 'profile.password.requirements.special',
    regex: /[!@#$%^&*(),.?":{}|<>]/,
    met: false
  }
]

// Status Message Component
const StatusAlert = ({ status, onDismiss }: { status: StatusMessage; onDismiss: () => void }) => {
  if (!status.show) return null

  const getIcon = () => {
    switch (status.type) {
      case 'success':
        return <CheckCircle className="h-4 w-4" />
      case 'error':
        return <AlertTriangle className="h-4 w-4" />
      case 'info':
        return <Info className="h-4 w-4" />
    }
  }

  const getStyles = () => {
    switch (status.type) {
      case 'success':
        return "bg-green-50 border-green-200 text-green-800"
      case 'error':
        return "bg-red-50 border-red-200 text-red-800"
      case 'info':
        return "bg-blue-50 border-blue-200 text-blue-800"
    }
  }

  return (
    <Alert className={cn("mb-4 animate-in fade-in duration-300", getStyles())}>
      {getIcon()}
      <AlertDescription className="flex items-center justify-between">
        <span>{status.message}</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          className="h-6 w-6 p-0 hover:bg-transparent"
        >
          <X className="h-3 w-3" />
        </Button>
      </AlertDescription>
    </Alert>
  )
}

export const ProfileDialog: React.FC<ProfileDialogProps> = ({
  isOpen,
  onClose,
  onLogout,
  onUserUpdate
}) => {
  const { t } = useTranslation()

  const [activeTab, setActiveTab] = useState("profile")
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState("")

  // Status message state
  const [statusMessage, setStatusMessage] = useState<StatusMessage>({
    type: 'info',
    message: '',
    show: false
  })

  // User data state
  const [userData, setUserData] = useState<UserData | null>(null)
  const [isLoadingProfile, setIsLoadingProfile] = useState(false)

  // Username change state
  const [userName, setUserName] = useState("")
  const [isEditingUsername, setIsEditingUsername] = useState(false)
  const [isSavingUsername, setIsSavingUsername] = useState(false)

  // Password change state
  const [passwordData, setPasswordData] = useState<PasswordChangeData>({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  })
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  })
  const [passwordRequirements, setPasswordRequirements] = useState<PasswordRequirement[]>(createPasswordRequirements())
  const [isPasswordValid, setIsPasswordValid] = useState(false)
  const [isChangingPassword, setIsChangingPassword] = useState(false)

  const [isDeletingAccount, setIsDeletingAccount] = useState(false)
  const [isExportingData, setIsExportingData] = useState(false)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_FLASK_URL || "http://localhost:14440/api/v1"

  // Status message helper functions
  const showStatus = (type: 'success' | 'error' | 'info', message: string) => {
    setStatusMessage({ type, message, show: true })

    // Auto-hide after 8 seconds
    setTimeout(() => {
      setStatusMessage(prev => ({ ...prev, show: false }))
    }, 8000)
  }

  const hideStatus = () => {
    setStatusMessage(prev => ({ ...prev, show: false }))
  }

  // Load user profile when dialog opens
  useEffect(() => {
    if (isOpen && !userData) {
      loadUserProfile()
    }
  })

  // Hide status when tab changes
  useEffect(() => {
    hideStatus()
  }, [activeTab])

  // Password validation
  useEffect(() => {
    const { newPassword } = passwordData
    const updatedRequirements = passwordRequirements.map(req => ({
      ...req,
      met: req.regex.test(newPassword)
    }))

    setPasswordRequirements(updatedRequirements)
    setIsPasswordValid(updatedRequirements.every(req => req.met) && newPassword.length >= 8)
  }, [passwordData, passwordData.newPassword, passwordRequirements])

  // Update username when userData changes
  useEffect(() => {
    if (userData) {
      setUserName(userData.username || "")
    }
  }, [userData])

  const loadUserProfile = async () => {
    setIsLoadingProfile(true)
    hideStatus()

    try {
      const response = await fetch(`${API_BASE_URL}/user/profile`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        const data = await response.json()
        const user = data.user
        const profileData: UserData = {
          email: user.email,
          username: user.username || "",
          joinDate: user.joinDate || "",
          id: user.id,
          role: user.role,
          confirmed: user.confirmed
        }
        setUserData(profileData)
        setUserName(user.username || "")
      } else {
        const error = await response.json()
        console.error('Failed to load profile:', error)
        showStatus('error', t("profile.errors.load_failed"))
      }
    } catch (error) {
      console.error('Error loading profile:', error)
      showStatus('error', t("profile.errors.network_error"))
    } finally {
      setIsLoadingProfile(false)
    }
  }

  const handleUsernameChange = async () => {
    if (!userName.trim()) {
      showStatus('error', t("profile.username.errors.empty"))
      return
    }

    if (userName.trim().length < 3) {
      showStatus('error', t("profile.username.errors.too_short"))
      return
    }

    setIsSavingUsername(true)
    hideStatus()

    try {
      const response = await fetch(`${API_BASE_URL}/user/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: userName.trim() })
      })

      if (response.ok) {
        const data = await response.json()
        setIsEditingUsername(false)

        // Update local state
        if (userData) {
          const updatedUserData = { ...userData, username: userName.trim() }
          setUserData(updatedUserData)
          onUserUpdate?.(updatedUserData)
        }

        showStatus('success', data.message || t("profile.username.success"))
      } else {
        const error = await response.json()
        if (error.error.includes("already taken")) {
          showStatus('error', t("profile.username.errors.taken"))
        } else {
          showStatus('error', error.error || t("profile.username.errors.update_failed"))
        }
      }
    } catch (error) {
      console.error('Username change error:', error)
      showStatus('error', t("profile.errors.network_error"))
    } finally {
      setIsSavingUsername(false)
    }
  }

  const handlePasswordChange = async () => {
    if (!isPasswordValid) {
      showStatus('error', t("profile.password.errors.requirements_not_met"))
      return
    }

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      showStatus('error', t("profile.password.errors.passwords_mismatch"))
      return
    }

    if (!passwordData.currentPassword) {
      showStatus('error', t("profile.password.errors.current_required"))
      return
    }

    setIsChangingPassword(true)
    hideStatus()

    try {
      const response = await fetch(`${API_BASE_URL}/user/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          currentPassword: passwordData.currentPassword,
          newPassword: passwordData.newPassword
        })
      })

      if (response.ok) {
        const data = await response.json()
        showStatus('success', data.message || t("profile.password.success"))
        setPasswordData({ currentPassword: "", newPassword: "", confirmPassword: "" })
      } else {
        const error = await response.json()
        if (error.error.includes("incorrect")) {
          showStatus('error', t("profile.password.errors.current_incorrect"))
        } else if (error.error.includes("same")) {
          showStatus('error', t("profile.password.errors.same_as_current"))
        } else {
          showStatus('error', error.error || t("profile.password.errors.change_failed"))
        }
      }
    } catch (error) {
      console.error('Password change error:', error)
      showStatus('error', t("profile.errors.network_error"))
    } finally {
      setIsChangingPassword(false)
    }
  }

  const handleAccountDelete = async () => {
    if (deleteConfirmText !== t("profile.delete.confirmation_text")) {
      showStatus('error', t("profile.delete.errors.confirmation_mismatch"))
      return
    }

    setIsDeletingAccount(true)
    hideStatus()

    try {
      const response = await fetch(`${API_BASE_URL}/user/delete-account`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ confirmation: deleteConfirmText })
      })

      if (response.ok) {
        const data = await response.json()
        showStatus('success', data.message || t("profile.delete.success"))

        // Logout after successful deletion (with delay)
        setTimeout(() => {
          onLogout()
        }, 3000)
      } else {
        const error = await response.json()
        showStatus('error', error.error || t("profile.delete.errors.delete_failed"))
      }
    } catch (error) {
      console.error('Account deletion error:', error)
      showStatus('error', t("profile.errors.network_error"))
    } finally {
      setIsDeletingAccount(false)
      setShowDeleteConfirm(false)
      setDeleteConfirmText("")
    }
  }

  const handleExportData = async () => {
    setIsExportingData(true)
    hideStatus()

    try {
      const response = await fetch(`${API_BASE_URL}/user/export-data`, {
        method: 'GET',
        credentials: 'include'
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'user-data-export.json'
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        showStatus('success', t("profile.export.success"))
      } else {
        const error = await response.json()
        showStatus('error', error.error || t("profile.export.errors.export_failed"))
      }
    } catch (error) {
      console.error('Data export error:', error)
      showStatus('error', t("profile.errors.network_error"))
    } finally {
      setIsExportingData(false)
    }
  }

  const resetDialog = () => {
    setActiveTab("profile")
    setShowDeleteConfirm(false)
    setDeleteConfirmText("")
    setPasswordData({ currentPassword: "", newPassword: "", confirmPassword: "" })
    setIsEditingUsername(false)
    hideStatus()
    if (userData) {
      setUserName(userData.username || "")
    }
  }

  const handleDialogClose = () => {
    resetDialog()
    onClose()
  }

  // Loading state
  if (isLoadingProfile) {
    return (
      <Dialog open={isOpen} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-md">
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="mt-4 text-sm text-muted-foreground">{t("profile.loading")}</p>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  // Error state
  if (!userData) {
    return (
      <Dialog open={isOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="sm:max-w-md">
          <div className="flex flex-col items-center justify-center py-8">
            <AlertTriangle className="h-8 w-8 text-destructive" />
            <p className="mt-4 text-sm text-muted-foreground text-center">
              {t("profile.errors.load_failed")}
            </p>
            <Button onClick={loadUserProfile} className="mt-4">
              {t("common.try_again")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleDialogClose}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            {t("profile.title")}
          </DialogTitle>
          <DialogDescription>
            {t("profile.description")}
          </DialogDescription>
        </DialogHeader>

        {/* Status Message - Always at top */}
        <StatusAlert status={statusMessage} onDismiss={hideStatus} />

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="profile" className="flex items-center gap-1">
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">{t("profile.tabs.profile")}</span>
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-1">
              <Lock className="h-4 w-4" />
              <span className="hidden sm:inline">{t("profile.tabs.security")}</span>
            </TabsTrigger>
            <TabsTrigger value="advanced" className="flex items-center gap-1">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">{t("profile.tabs.advanced")}</span>
            </TabsTrigger>
          </TabsList>

          {/* PROFILE TAB */}
          <TabsContent value="profile" className="space-y-6 max-h-80 overflow-y-auto">
            <div className="space-y-4">
              {/* Email - readonly */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">{t("profile.email.label")}</Label>
                <div className="flex items-center gap-2 p-3 bg-muted/50 rounded-md">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{userData.email}</span>
                </div>
              </div>

              {/* Username - editable */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">{t("profile.username.label")}</Label>
                {!isEditingUsername ? (
                  <div className="flex items-center justify-between p-3 bg-background border rounded-md hover:bg-muted/30 transition-colors">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{userName || t("profile.username.not_set")}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsEditingUsername(true)}
                      className="h-8 px-2 hover:bg-muted"
                      disabled={isSavingUsername}
                    >
                      <Edit2 className="h-3 w-3" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <Input
                      value={userName}
                      onChange={(e) => setUserName(e.target.value)}
                      placeholder={t("profile.username.placeholder")}
                      className="flex-1"
                      disabled={isSavingUsername}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleUsernameChange()
                        } else if (e.key === 'Escape') {
                          setIsEditingUsername(false)
                          setUserName(userData.username || "")
                        }
                      }}
                    />
                    <Button
                      onClick={handleUsernameChange}
                      disabled={isSavingUsername || !userName.trim()}
                      size="sm"
                      className="min-w-[80px]"
                    >
                      {isSavingUsername ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        t("common.save")
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setIsEditingUsername(false)
                        setUserName(userData.username || "")
                      }}
                      size="sm"
                      disabled={isSavingUsername}
                    >
                      {t("common.cancel")}
                    </Button>
                  </div>
                )}
              </div>

              <Separator />

              {/* Join date */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">{t("profile.join_date.label")}</Label>
                <div className="flex items-center gap-2 p-3 bg-muted/50 rounded-md">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{userData.joinDate || t("profile.join_date.unknown")}</span>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* SECURITY TAB */}
          <TabsContent value="security" className="space-y-6 max-h-100 overflow-y-auto">
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-medium mb-4">{t("profile.password.title")}</h3>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="current-password">{t("profile.password.current")}</Label>
                    <div className="relative">
                      <Input
                        id="current-password"
                        type={showPasswords.current ? "text" : "password"}
                        value={passwordData.currentPassword}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, currentPassword: e.target.value }))}
                        placeholder={t("profile.password.current_placeholder")}
                        disabled={isChangingPassword}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0"
                        onClick={() => setShowPasswords(prev => ({ ...prev, current: !prev.current }))}
                        disabled={isChangingPassword}
                      >
                        {showPasswords.current ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="new-password">{t("profile.password.new")}</Label>
                    <div className="relative">
                      <Input
                        id="new-password"
                        type={showPasswords.new ? "text" : "password"}
                        value={passwordData.newPassword}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                        placeholder={t("profile.password.new_placeholder")}
                        className={cn(
                          passwordData.newPassword && !isPasswordValid && "border-orange-500"
                        )}
                        disabled={isChangingPassword}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0"
                        onClick={() => setShowPasswords(prev => ({ ...prev, new: !prev.new }))}
                        disabled={isChangingPassword}
                      >
                        {showPasswords.new ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>

                    {/* Password requirements */}
                    {passwordData.newPassword && (
                      <div className="mt-3 p-3 border border-border/50 rounded-lg bg-muted/30">
                        <p className="text-sm font-medium text-muted-foreground mb-2">
                          {t("profile.password.requirements.title")}
                        </p>
                        <ul className="space-y-1">
                          {passwordRequirements.map((req) => (
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
                              {t(req.label)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">{t("profile.password.confirm")}</Label>
                    <div className="relative">
                      <Input
                        id="confirm-password"
                        type={showPasswords.confirm ? "text" : "password"}
                        value={passwordData.confirmPassword}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                        placeholder={t("profile.password.confirm_placeholder")}
                        className={cn(
                          passwordData.confirmPassword &&
                          passwordData.newPassword !== passwordData.confirmPassword &&
                          "border-orange-500"
                        )}
                        disabled={isChangingPassword}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0"
                        onClick={() => setShowPasswords(prev => ({ ...prev, confirm: !prev.confirm }))}
                        disabled={isChangingPassword}
                      >
                        {showPasswords.confirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>

                    {passwordData.confirmPassword && passwordData.newPassword !== passwordData.confirmPassword && (
                      <p className="text-xs text-orange-600 flex items-center gap-1">
                        <X className="h-3 w-3" />
                        {t("profile.password.errors.passwords_mismatch")}
                      </p>
                    )}

                    {passwordData.confirmPassword && passwordData.newPassword === passwordData.confirmPassword && passwordData.confirmPassword.length > 0 && (
                      <p className="text-xs text-green-600 flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" />
                        {t("profile.password.passwords_match")}
                      </p>
                    )}
                  </div>

                  <Button
                    onClick={handlePasswordChange}
                    disabled={!isPasswordValid || passwordData.newPassword !== passwordData.confirmPassword || isChangingPassword || !passwordData.currentPassword}
                    className="w-full"
                  >
                    {isChangingPassword ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        {t("profile.password.changing")}
                      </>
                    ) : (
                      t("profile.password.change_button")
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* ADVANCED TAB */}
          <TabsContent value="advanced" className="space-y-6 max-h-100 overflow-y-auto">
            <div className="space-y-6">
              <div className="p-4 border rounded-lg hover:bg-muted/30 transition-colors">
                <h3 className="text-lg font-medium mb-2">{t("profile.export.title")}</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  {t("profile.export.description")}
                </p>
                <Button
                  onClick={handleExportData}
                  variant="outline"
                  className="w-full"
                  disabled={isExportingData}
                >
                  {isExportingData ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      {t("profile.export.exporting")}
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-2" />
                      {t("profile.export.button")}
                    </>
                  )}
                </Button>
              </div>

              <Separator />

              <div className="p-4 border border-destructive/20 rounded-lg">
                <h3 className="text-lg font-medium mb-2 flex items-center gap-2 text-destructive">
                  <AlertTriangle className="h-5 w-5" />
                  {t("profile.delete.title")}
                </h3>

                {!showDeleteConfirm ? (
                  <div>
                    <p className="text-sm text-muted-foreground mb-4">
                      {t("profile.delete.description")}
                    </p>
                    <Button
                      onClick={() => setShowDeleteConfirm(true)}
                      variant="destructive"
                      className="w-full"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      {t("profile.delete.button")}
                    </Button>
                  </div>
                ) : (
                  <Alert className="border-destructive bg-destructive/5">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="space-y-3">
                        <p className="font-medium">{t("profile.delete.warning")}</p>
                        <p className="text-sm">
                          {t("profile.delete.instruction", {
                            text: t("profile.delete.confirmation_text")
                          })}
                        </p>
                        <Input
                          value={deleteConfirmText}
                          onChange={(e) => setDeleteConfirmText(e.target.value)}
                          placeholder={t("profile.delete.confirmation_text")}
                          className="font-mono"
                          disabled={isDeletingAccount}
                        />
                        <div className="flex gap-2">
                          <Button
                            onClick={handleAccountDelete}
                            disabled={deleteConfirmText !== t("profile.delete.confirmation_text") || isDeletingAccount}
                            variant="destructive"
                            className="flex-1"
                          >
                            {isDeletingAccount ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                {t("profile.delete.deleting")}
                              </>
                            ) : (
                              t("profile.delete.confirm_button")
                            )}
                          </Button>
                          <Button
                            onClick={() => {
                              setShowDeleteConfirm(false)
                              setDeleteConfirmText("")
                            }}
                            variant="outline"
                            className="flex-1"
                            disabled={isDeletingAccount}
                          >
                            {t("common.cancel")}
                          </Button>
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="flex justify-between sm:justify-between">
          <Button variant="outline" onClick={handleDialogClose}>
            {t("common.close")}
          </Button>
          <Button variant="destructive" onClick={onLogout}>
            {t("common.logout")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
