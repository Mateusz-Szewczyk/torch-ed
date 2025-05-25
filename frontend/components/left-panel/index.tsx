"use client"

import type React from "react"
import { useState, useEffect, useContext } from "react"
import { useRouter } from "next/navigation"
import { useTranslation } from "react-i18next"
import {
  Home,
  BookOpen,
  TestTube,
  Mail,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  UserCircle,
  Settings,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { LoginRegisterDialog } from "@/components/LoginRegisterDialog"
import { SettingsDialog } from "@/components/SettingsDialog"
import ManageFileDialog from "@/components/ManageFileDialog"
import FeedbackModal from "@/components/FeedbackModal"
import { ConversationContext } from "@/contexts/ConversationContext"
import { AuthContext } from "@/contexts/AuthContext"
import { ConversationList } from "./conversation-list"
import { ProfileDialog } from "./profile-dialog"
import { CustomTooltip } from "@/components/CustomTooltip"

interface Conversation {
  id: number
  title: string | null
  created_at: string
}

interface LeftPanelProps {
  isPanelVisible: boolean
  isMobile: boolean
  togglePanel: () => void
}

const LeftPanel: React.FC<LeftPanelProps> = ({ isPanelVisible, isMobile, togglePanel }) => {
  const { isAuthenticated, setIsAuthenticated } = useContext(AuthContext)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const router = useRouter()
  const { t } = useTranslation()
  const { setCurrentConversationId } = useContext(ConversationContext)

  // Dialog states
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false)
  const [isProfileOpen, setIsProfileOpen] = useState(false)

  const FLASK_API_BASE_URL = process.env.NEXT_PUBLIC_API_FLASK_URL || "http://localhost:14440/api/v1"
  const AI_API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"
  const BE_API_BASE_URL = `${FLASK_API_BASE_URL}/auth`

  // Fetch conversations if authenticated
  useEffect(() => {
    if (!isAuthenticated) return
    const fetchConversations = async () => {
      try {
        const response = await fetch(`${AI_API_BASE_URL}/chats/`, {
          credentials: "include",
          headers: { Authorization: "TorchED_AUTH" },
        })
        if (response.ok) {
          const data: Conversation[] = await response.json()
          setConversations(data)
        } else {
          console.error("Failed to fetch conversations:", response.statusText)
        }
      } catch (error: unknown) {
        console.error("Error fetching conversations:", error)
      }
    }
    fetchConversations()
  }, [AI_API_BASE_URL, isAuthenticated])

  // Create a new conversation
  const handleNewConversation = async () => {
    try {
      const response = await fetch(`${AI_API_BASE_URL}/chats/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
      if (response.ok) {
        const newConv: Conversation = await response.json()
        setConversations((prev) => [...prev, newConv])
        setCurrentConversationId(newConv.id)
        router.push(`/chat`)
      } else {
        console.error("Failed to create conversation:", response.statusText)
      }
    } catch (error: unknown) {
      console.error("Error creating conversation:", error)
    }
  }

  // Navigate to a conversation
  const handleConversationClick = (conversationId: number) => {
    setCurrentConversationId(conversationId)
    router.push(`/chat`)
  }

  // Handle logout
  const handleLogout = async () => {
    try {
      const res = await fetch(`${BE_API_BASE_URL}/logout`, {
        method: "GET",
        credentials: "include",
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.error || "Logout failed")
      }
      setIsProfileOpen(false)
      setIsAuthenticated(false)
      localStorage.removeItem("token")
      router.push("/")
    } catch (err: unknown) {
      console.error("Error logging out:", err)
      if (err instanceof Error) {
        alert("Nie udało się wylogować: " + err.message)
      } else {
        alert("Nie udało się wylogować.")
      }
    }
  }

  // Determine if we should render the mobile overlay
  const shouldRenderMobileOverlay = isMobile && isPanelVisible

  return (
    <>
      {/* Mobile backdrop */}
      {shouldRenderMobileOverlay && (
        <div
          className="fixed inset-0 bg-black/30 z-40 md:hidden transition-opacity duration-300"
          onClick={togglePanel}
          aria-hidden="true"
        />
      )}

      {/* Main Panel Container */}
      <div
        className={`
          fixed top-0 left-0 h-full bg-card text-foreground
          shadow-md dark:shadow-slate-900/20
          transition-all duration-300 ease-in-out z-50 flex flex-col
          ${isMobile ? (isPanelVisible ? "w-[280px] max-w-[80vw]" : "w-0") : isPanelVisible ? "w-64" : "w-16"}
          ${isMobile && !isPanelVisible ? "overflow-hidden" : ""}
        `}
      >
        {(!isMobile || isPanelVisible) && (
          <>
            {/* Panel Header */}
            <div className="p-4 flex items-center justify-between border-b border-border/40">
              <div
                className={`flex items-center transition-opacity duration-300 ${
                  isPanelVisible ? "opacity-100" : "opacity-0 w-0 pointer-events-none"
                }`}
              >
                <div className="w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center mr-2">
                  <span className="text-primary font-bold">T</span>
                </div>
                <h2 className="font-semibold text-lg">TorchED</h2>
              </div>

              {/* Header buttons */}
              <div className="flex items-center gap-2">
                <CustomTooltip content={t("home")}>
                  <Button
                    asChild
                    variant="ghost"
                    className="p-2 rounded-full hover:bg-secondary/80 transition-colors duration-200"
                    aria-label={t("home")}
                  >
                    <Link href="/">
                      <Home className="h-5 w-5" />
                    </Link>
                  </Button>
                </CustomTooltip>

                {isMobile && (
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={togglePanel}>
                    <X className="h-4 w-4" />
                    <span className="sr-only">Close</span>
                  </Button>
                )}
              </div>
            </div>

            {/* Main Navigation */}
            <div className="flex-grow overflow-y-auto p-1 space-y-4">
              {/* Primary Navigation */}
              <div className="space-y-2 p-2">
                {isPanelVisible && (
                  <h3 className="text-xs uppercase text-muted-foreground font-medium px-2 mb-2">{t("navigation")}</h3>
                )}

                {isAuthenticated && (
                  <>
                    <NavItem
                      icon={BookOpen}
                      label={t("flashcards")}
                      href="/flashcards"
                      isPanelVisible={isPanelVisible}
                    />

                    <NavItem icon={TestTube} label={t("tests")} href="/tests" isPanelVisible={isPanelVisible} />

                    <ManageFileDialog isPanelVisible={isPanelVisible} />
                  </>
                )}
              </div>

              {/* Conversations Section */}
              {isAuthenticated && (
                <div className="space-y-1 p-2">
                  {isPanelVisible && (
                    <h3 className="text-xs uppercase text-muted-foreground font-medium px-2 mb-2">
                      {t("conversations")}
                    </h3>
                  )}

                  {isPanelVisible ? (
                    <ConversationList
                      conversations={conversations}
                      onConversationClick={handleConversationClick}
                      onNewConversation={handleNewConversation}
                      AI_API_BASE_URL={AI_API_BASE_URL}
                      setConversations={setConversations}
                      setCurrentConversationId={setCurrentConversationId}
                    />
                  ) : (
                    <CustomTooltip content={t("conversations")}>
                      <Button
                        variant="ghost"
                        className="w-full flex justify-center"
                        onClick={() => {
                          togglePanel()
                          // After panel expands, focus on the conversations section
                          setTimeout(() => {
                            document.getElementById("conversations-section")?.focus()
                          }, 300)
                        }}
                      >
                        <MessageSquare className="h-5 w-5" />
                      </Button>
                    </CustomTooltip>
                  )}
                </div>
              )}
            </div>

            {/* Footer Section */}
            <div className="border-t border-border/40 p-3 space-y-2">
              <NavItem
                icon={Mail}
                label={t("send_feedback")}
                isPanelVisible={isPanelVisible}
                onClick={() => setIsFeedbackOpen(true)}
              />

              <SettingsDialog>
                <NavItem icon={Settings} label={t("settings")} isPanelVisible={isPanelVisible} />
              </SettingsDialog>

              {isAuthenticated ? (
                <NavItem
                  icon={UserCircle}
                  label={t("my_profile")}
                  isPanelVisible={isPanelVisible}
                  onClick={() => setIsProfileOpen(true)}
                />
              ) : (
                <LoginRegisterDialog setIsAuthenticated={setIsAuthenticated}>
                  <NavItem
                    icon={UserCircle}
                    label={t("login_register")}
                    isPanelVisible={isPanelVisible}
                    variant="default"
                  />
                </LoginRegisterDialog>
              )}
            </div>
          </>
        )}

        {/* Panel toggle button */}
        {!isMobile && (
          <Button
            variant="ghost"
            className={`
              absolute top-1/2 -right-3 transform -translate-y-1/2
              h-6 w-6 rounded-full p-0
              bg-background border border-border/60
              shadow-sm hover:shadow transition-all duration-200
              flex items-center justify-center
            `}
            onClick={togglePanel}
            aria-label={isPanelVisible ? t("collapse_sidebar") : t("expand_sidebar")}
          >
            {isPanelVisible ? <ChevronLeft className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </Button>
        )}
      </div>

      {/* Modals and Dialogs */}
      <FeedbackModal isOpen={isFeedbackOpen} onClose={() => setIsFeedbackOpen(false)} />

      <ProfileDialog isOpen={isProfileOpen} onClose={() => setIsProfileOpen(false)} onLogout={handleLogout} />
    </>
  )
}

// Helper component for navigation items
interface NavItemProps {
  icon: React.ElementType
  label: string
  href?: string
  isPanelVisible: boolean
  isActive?: boolean
  variant?: "default" | "ghost" | "outline"
  onClick?: () => void
}

const NavItem: React.FC<NavItemProps> = ({
  icon: Icon,
  label,
  href,
  isPanelVisible,
  isActive = false,
  variant = "ghost",
  onClick,
}) => {
  const content = (
    <>
      <Icon className={`h-5 w-5 ${isActive ? "text-primary" : ""}`} />
      {isPanelVisible && <span className={`ml-3 font-medium ${isActive ? "text-primary" : ""}`}>{label}</span>}
      {isActive && isPanelVisible && <span className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary" />}
    </>
  )

  const buttonClass = `
    w-full group relative overflow-hidden
    ${isPanelVisible ? "justify-start" : "justify-center"}
    ${isActive ? "bg-primary/10 text-primary" : "hover:bg-secondary/80 hover:text-primary"}
    transition-all duration-200
  `

  if (!isPanelVisible) {
    return (
      <CustomTooltip content={label}>
        {href ? (
          <Button asChild variant={variant} className={buttonClass} onClick={onClick}>
            <Link href={href}>{content}</Link>
          </Button>
        ) : (
          <Button variant={variant} className={buttonClass} onClick={onClick}>
            {content}
          </Button>
        )}
      </CustomTooltip>
    )
  }

  return href ? (
    <Button asChild variant={variant} className={buttonClass} onClick={onClick}>
      <Link href={href}>{content}</Link>
    </Button>
  ) : (
    <Button variant={variant} className={buttonClass} onClick={onClick}>
      {content}
    </Button>
  )
}

export default LeftPanel
