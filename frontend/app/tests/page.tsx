"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import {motion, AnimatePresence, Variants} from "framer-motion"
import { EditExamDialog } from "@/components/EditExamDialog"
import { CustomTooltip } from "@/components/CustomTooltip"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  PlusCircle,
  Info,
  ChevronRight,
  MoreHorizontal,
  Edit,
  Trash2,
  Search,
  Clock,
  X,
  ArrowLeft,
  SortAsc,
  SortDesc,
  Filter,
  CheckCircle2,
  TestTube,
  Target,
  Share2,
  Download,
  Copy,
  Users,
  TrendingUp,
} from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { StudyExam } from "@/components/StudyExam"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import type { Exam } from "@/types"

// Interfaces for API responses
interface ShareCodeInfo {
  share_code: string
  content_id: number
  exam_name: string
  exam_description: string
  question_count: number
  creator_id: number
  created_at: string
  access_count: number
  already_added?: boolean
  is_own_exam?: boolean
}

interface ShareCode {
  share_code: string
  content_id: number
  content_name: string
  item_count: number
  created_at: string
  access_count: number
}

interface ShareStatistics {
  created_share_codes: number
  added_shared_exams: number
  total_exam_accesses: number
}

interface ErrorResponse {
  detail: string | { msg: string }[]
}

// Animation variants for framer-motion
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring" as const, stiffness: 300, damping: 24 },
  },
} satisfies Variants;

// Sort options for exams
type SortOption = "name" | "questions" | "recent"
type SortDirection = "asc" | "desc"

export default function ExamsPage() {
  const [exams, setExams] = useState<Exam[]>([])
  const [filteredExams, setFilteredExams] = useState<Exam[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [sortBy, setSortBy] = useState<SortOption>("recent")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")
  const [isSearchFocused, setIsSearchFocused] = useState<boolean>(false)
  const [studyingExam, setStudyingExam] = useState<Exam | null>(null)

  // Sharing related states
  const [shareCodeInput, setShareCodeInput] = useState<string>("")
  const [shareCodeInfo, setShareCodeInfo] = useState<ShareCodeInfo | null>(null)
  const [shareCodeInfoLoading, setShareCodeInfoLoading] = useState<boolean>(false)
  const [myCodes, setMyCodes] = useState<ShareCode[]>([])
  const [shareStats, setShareStats] = useState<ShareStatistics | null>(null)
  const [showAddByCodeModal, setShowAddByCodeModal] = useState<boolean>(false)
  const [showManageSharesModal, setShowManageSharesModal] = useState<boolean>(false)

  const { t } = useTranslation()
  const searchInputRef = useRef<HTMLInputElement>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"
  const EXAMS_API_BASE = `${API_BASE_URL}/exams/`
  const CONVERSATIONS_URL = `${API_BASE_URL}/chats/`

  const fetchExams = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // ZAWSZE pobieraj udostępnione egzaminy
      const res = await fetch(`${EXAMS_API_BASE}?include_shared=true`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || t("error_fetch_exams") || "Error fetching exams.")
      }
      const data: Exam[] = await res.json()
      setExams(data)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError(t("error_unexpected_fetch_exams") || "Unexpected error fetching exams.")
      }
      console.error("Error fetching exams:", err)
    } finally {
      setLoading(false)
    }
  }, [EXAMS_API_BASE, t])

  useEffect(() => {
    fetchExams()
  }, [fetchExams])

  // Fetch user's share codes
  const fetchMyCodes = useCallback(async () => {
    try {
      const response = await fetch(`${EXAMS_API_BASE}my-shared-codes`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })

      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || t("failed_fetch_share_codes"))
      }

      const data: ShareCode[] = await response.json()
      setMyCodes(data)
    } catch (err: unknown) {
      console.error("Error fetching share codes:", err)
      if (err instanceof Error) {
        toast.error(`${t("error_fetching_share_codes")}: ${err.message}`)
      }
    }
  }, [EXAMS_API_BASE, t])

  // Fetch share statistics
  const fetchShareStats = useCallback(async () => {
    try {
      const response = await fetch(`${EXAMS_API_BASE}share-statistics`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })

      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || t("failed_fetch_statistics"))
      }

      const data: ShareStatistics = await response.json()
      setShareStats(data)
    } catch (err: unknown) {
      console.error("Error fetching share statistics:", err)
      if (err instanceof Error) {
        toast.error(`${t("error_fetching_statistics")}: ${err.message}`)
      }
    }
  }, [EXAMS_API_BASE, t])

  // Get share code info - NAPRAWIONE: dodane useCallback
  const handleGetShareCodeInfo = useCallback(async (code: string) => {
    if (code.length !== 12) {
      setShareCodeInfo(null)
      return
    }

    setShareCodeInfoLoading(true)
    setShareCodeInfo(null)

    try {
      const response = await fetch(`${EXAMS_API_BASE}share-info/${code}`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })

      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || t("invalid_share_code"))
      }

      const data: ShareCodeInfo = await response.json()
      setShareCodeInfo(data)
    } catch (err: unknown) {
      setShareCodeInfo(null)
      if (err instanceof Error) {
        toast.error(err.message)
      } else {
        toast.error(t("failed_get_exam_information"))
      }
      console.error("Error fetching share code info:", err)
    } finally {
      setShareCodeInfoLoading(false)
    }
  }, [EXAMS_API_BASE, t])

  // Add exam by code
  const handleAddByCode = async () => {
    if (!shareCodeInput.trim() || shareCodeInput.length !== 12) {
      toast.error(t("enter_valid_share_code"))
      return
    }

    try {
      const response = await fetch(`${EXAMS_API_BASE}add-by-code`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: shareCodeInput.trim().toUpperCase() }),
      })

      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || t("failed_add_exam"))
      }

      const result = await response.json()
      toast.success(result.message || t("exam_added_successfully"))

      setShareCodeInput("")
      setShareCodeInfo(null)
      setShowAddByCodeModal(false)

      // Refresh exams
      fetchExams()
    } catch (err: unknown) {
      if (err instanceof Error) {
        toast.error(err.message)
      } else {
        toast.error(t("failed_add_exam"))
      }
      console.error("Error adding exam by code:", err)
    }
  }

  // Share exam
  const handleShare = async (examId: number) => {
    try {
      const response = await fetch(`${EXAMS_API_BASE}${examId}/share`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })

      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || t("failed_create_share_code"))
      }

      const result = await response.json()

      // Copy to clipboard
      await navigator.clipboard.writeText(result.share_code)
      toast.success(t("share_code_created_and_copied", { code: result.share_code }))

      // Refresh exams to update is_shared status
      fetchExams()
      if (showManageSharesModal) {
        fetchMyCodes()
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        toast.error(err.message)
      } else {
        toast.error(t("failed_create_share_code"))
      }
      console.error("Error sharing exam:", err)
    }
  }

  // Remove shared exam
  const handleRemoveSharedExam = async (examId: number) => {
    try {
      const response = await fetch(`${EXAMS_API_BASE}shared/${examId}`, {
        method: "DELETE",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })

      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || t("failed_remove_exam"))
      }

      const result = await response.json()
      toast.success(result.message || t("exam_removed_from_library"))

      // Refresh exams
      fetchExams()
    } catch (err: unknown) {
      if (err instanceof Error) {
        toast.error(err.message)
      } else {
        toast.error(t("failed_remove_exam"))
      }
      console.error("Error removing shared exam:", err)
    }
  }

  // Deactivate share code
  const handleDeactivateCode = async (shareCode: string) => {
    try {
      const response = await fetch(`${EXAMS_API_BASE}shared-code/${shareCode}/deactivate`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })

      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || t("failed_deactivate_code"))
      }

      toast.success(t("share_code_deactivated_successfully"))
      fetchMyCodes()
    } catch (err: unknown) {
      if (err instanceof Error) {
        toast.error(err.message)
      } else {
        toast.error(t("failed_deactivate_share_code"))
      }
      console.error("Error deactivating share code:", err)
    }
  }

  // Copy share code to clipboard
  const handleCopyCode = async (code: string, event?: React.MouseEvent) => {
    if (event) {
      event.stopPropagation()
      event.preventDefault()
    }
    try {
      await navigator.clipboard.writeText(code)
      toast.success(t("share_code_copied_to_clipboard"))
    } catch {
      toast.error(t("failed_copy_to_clipboard"))
    }
  }

  // Watch for share code input changes - NAPRAWIONE: dodane handleGetShareCodeInfo do dependencies
  useEffect(() => {
    if (shareCodeInput.length === 12) {
      handleGetShareCodeInfo(shareCodeInput.toUpperCase())
    } else {
      setShareCodeInfo(null)
    }
  }, [shareCodeInput, handleGetShareCodeInfo])

  // Load shared data when manage modal opens
  useEffect(() => {
    if (showManageSharesModal) {
      fetchMyCodes()
      fetchShareStats()
    }
  }, [showManageSharesModal, fetchMyCodes, fetchShareStats])

  // Filter and sort exams based on search query and sort options
  useEffect(() => {
    let result = [...exams]

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (exam) =>
          exam.name.toLowerCase().includes(query) ||
          (exam.description && exam.description.toLowerCase().includes(query)),
      )
    }

    // Apply sorting
    result.sort((a, b) => {
      if (sortBy === "name") {
        return sortDirection === "asc" ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name)
      } else if (sortBy === "questions") {
        return sortDirection === "asc"
          ? a.questions.length - b.questions.length
          : b.questions.length - a.questions.length
      } else {
        // recent - using ID as a proxy for recency
        return sortDirection === "asc" ? a.id - b.id : b.id - a.id
      }
    })

    setFilteredExams(result)
  }, [exams, searchQuery, sortBy, sortDirection])

  const handleSave = async (updatedExam: Exam) => {
    try {
      const bodyData = {
        name: updatedExam.name,
        description: updatedExam.description,
        questions: updatedExam.questions.map((q) => ({
          id: q.id,
          text: q.text,
          answers: q.answers.map((a) =>
            a.id ? { id: a.id, text: a.text, is_correct: a.is_correct } : { text: a.text, is_correct: a.is_correct },
          ),
        })),
        conversation_id: updatedExam.conversation_id || 0,
      }

      if (updatedExam.id === 0) {
        const res = await fetch(EXAMS_API_BASE, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyData),
        })
        if (!res.ok) {
          const errorData = await res.json()
          throw new Error(errorData.detail || t("error_saving_exam") || "Error creating exam.")
        }
        const newExam: Exam = await res.json()
        setExams((prev) => [...prev, newExam])
      } else {
        const res = await fetch(`${EXAMS_API_BASE}${updatedExam.id}/`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyData),
        })
        if (!res.ok) {
          const errorData = await res.json()
          throw new Error(errorData.detail || t("error_saving_exam") || "Error updating exam.")
        }
        const updatedExamFromServer: Exam = await res.json()
        setExams((prev) => prev.map((exam) => (exam.id === updatedExamFromServer.id ? updatedExamFromServer : exam)))
      }
    } catch (err: unknown) {
      console.error("Error saving exam:", err)
      if (err instanceof Error) {
        setError(`${t("error_saving_exam")}: ${err.message}`)
      } else {
        setError(t("error_unexpected_saving_exam") || "Unexpected error saving exam.")
      }
    }
  }

  const handleDelete = async (examId: number) => {
    try {
      const res = await fetch(`${EXAMS_API_BASE}${examId}/`, {
        method: "DELETE",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || t("error_deleting_exam") || "Error deleting exam.")
      }
      setExams((prev) => prev.filter((exam) => exam.id !== examId))
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error("Error deleting exam:", err)
        setError(`${t("error_deleting_exam")}: ${err.message}`)
      } else {
        console.error(err)
        setError(t("error_unexpected_deleting_exam") || "Unexpected error deleting exam.")
      }
    }
  }

  const handleStudy = async (exam: Exam) => {
    try {
      let finalExam: Exam = exam

      // Sprawdź czy egzamin ma pytania
      if (!exam.questions || exam.questions.length === 0) {
        throw new Error(t("exam_has_no_questions"))
      }

      if (!exam.conversation_id || exam.conversation_id === 0) {
        const convRes = await fetch(CONVERSATIONS_URL, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ exam_id: exam.id, title: exam.name }),
        })
        if (!convRes.ok) {
          const convErr = await convRes.json()
          let errorMsg = t("failed_create_conversation")
          if (Array.isArray(convErr.detail)) {
            errorMsg = convErr.detail
              .map((detailErr: unknown) =>
                typeof detailErr === "object" && detailErr !== null && "msg" in detailErr
                  ? (detailErr as { msg: string }).msg
                  : String(detailErr),
              )
              .join(", ")
          } else if (typeof convErr.detail === "string") {
            errorMsg = convErr.detail
          }
          throw new Error(errorMsg)
        }
        const updatedExamResp = await fetch(`${EXAMS_API_BASE}${exam.id}/`, {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
        if (!updatedExamResp.ok) {
          const fetchErr = await updatedExamResp.json()
          throw new Error(fetchErr.detail || t("could_not_refetch_exam"))
        }
        finalExam = await updatedExamResp.json()
        setExams((prev) => prev.map((e) => (e.id === exam.id ? finalExam : e)))
      }

      setStudyingExam(finalExam)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t("error_starting_study")}: ${err.message}`)
      } else {
        setError(t("error_unexpected_starting_study") || "Unexpected error starting exam session.")
      }
      console.error("Error starting exam session:", err)
    }
  }

  const handleExitStudy = () => {
    setStudyingExam(null)
  }

  const handleClearSearch = () => {
    setSearchQuery("")
    if (searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }

  const toggleSortDirection = () => {
    setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"))
  }

  // Format date for display
  const formatDate = (dateString: string | null) => {
    if (!dateString) return ""
    const date = new Date(dateString)
    return new Intl.DateTimeFormat(navigator.language, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date)
  }

  // Loading state with skeleton UI
  if (loading) {
    return (
      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-8 max-w-7xl">
        <div className="flex flex-col items-center justify-center mb-8 md:mb-12">
          <div className="w-32 sm:w-48 h-8 sm:h-10 bg-muted animate-pulse rounded-md mb-3 sm:mb-4"></div>
          <div className="w-48 sm:w-64 h-4 sm:h-6 bg-muted animate-pulse rounded-md"></div>
        </div>

        <div className="w-full max-w-md mx-auto mb-6 sm:mb-8 bg-muted animate-pulse h-10 sm:h-11 rounded-md"></div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="bg-muted animate-pulse rounded-xl h-56 sm:h-64"></div>
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-8 flex items-center justify-center min-h-[50vh]">
        <Card className="w-full max-w-md border-destructive/20">
          <CardHeader className="pb-3 sm:pb-4">
            <CardTitle className="text-lg sm:text-2xl font-bold text-destructive flex items-center gap-2">
              <X className="h-5 w-5 sm:h-6 sm:w-6" />
              {t("error")}
            </CardTitle>
            <CardDescription className="text-sm sm:text-base">{t("error_occurred")}</CardDescription>
          </CardHeader>
          <CardContent className="pb-4 sm:pb-6">
            <p className="text-destructive/90 bg-destructive/5 p-3 sm:p-4 rounded-md border border-destructive/10 text-sm sm:text-base">{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchExams} className="w-full h-10 sm:h-11">
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t("try_again")}
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  // Study mode
  if (studyingExam) {
    return <StudyExam exam={studyingExam} onExit={handleExitStudy} />
  }

  // Main content
  return (
    <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-8 max-w-7xl">
      {/* Header */}
      <motion.div
        className="flex flex-col items-center justify-center mb-6 sm:mb-8 md:mb-12"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent mb-2 text-center">
          {t("tests")}
        </h1>
        <p className="text-muted-foreground text-center max-w-xl mb-2 text-sm sm:text-base px-2">
          {t("tests_description")}
        </p>
        <CustomTooltip content={t("tests_tooltip")}>
          <Button variant="ghost" size="sm" className="rounded-full h-8 w-8 p-0">
            <Info className="h-4 w-4" />
            <span className="sr-only">{t("more_information")}</span>
          </Button>
        </CustomTooltip>
      </motion.div>

      {exams.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="w-full max-w-2xl mx-auto border-dashed bg-background/50 backdrop-blur-sm">
            <CardHeader className="pb-3 sm:pb-4">
              <CardTitle className="text-xl sm:text-2xl font-bold text-center">{t("welcome_tests")}</CardTitle>
              <CardDescription className="text-center text-sm sm:text-base">{t("get_started_create_test")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center space-y-4 sm:space-y-6 py-8 sm:py-12">
              <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-primary/10 flex items-center justify-center">
                <TestTube className="h-10 w-10 sm:h-12 sm:w-12 text-primary" />
              </div>
              <p className="text-center text-muted-foreground max-w-md text-sm sm:text-base px-4">
                {t("no_tests_available_extended")}
              </p>
            </CardContent>
            <CardFooter className="flex flex-col sm:flex-row justify-center gap-3">
              <EditExamDialog
                exam={{
                  id: 0,
                  user_id: 0, // NAPRAWIONE: dodane user_id
                  name: "",
                  description: "",
                  created_at: "",
                  questions: []
                }}
                onSave={handleSave}
                trigger={
                  <Button className="w-full sm:w-auto h-10 sm:h-11" variant="default">
                    <PlusCircle className="h-4 w-4 sm:h-5 sm:w-5 mr-2" />
                    <span className="text-sm sm:text-base">{t("create_your_first_test")}</span>
                  </Button>
                }
              />
              <Button
                variant="outline"
                className="w-full sm:w-auto h-10 sm:h-11"
                onClick={() => setShowAddByCodeModal(true)}
              >
                <Download className="h-4 w-4 sm:h-5 sm:w-5 mr-2" />
                <span className="text-sm sm:text-base">{t("add_by_code")}</span>
              </Button>
            </CardFooter>
          </Card>
        </motion.div>
      ) : (
        <>
          {/* Search and Filter Bar - Mobile First */}
          <motion.div
            className="mb-6 sm:mb-8 space-y-3 sm:space-y-0 sm:flex sm:flex-row sm:gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            {/* Search Input - Full width on mobile */}
            <div
              className={cn(
                "relative w-full sm:flex-grow transition-all duration-300 rounded-lg",
                isSearchFocused ? "ring-2 ring-primary/20" : "",
              )}
            >
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                ref={searchInputRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("search_exams")}
                className="pl-10 pr-10 h-10 sm:h-11 bg-background/60 backdrop-blur-sm border-muted text-sm sm:text-base"
                onFocus={() => setIsSearchFocused(true)}
                onBlur={() => setIsSearchFocused(false)}
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 transform -translate-y-1/2 h-8 w-8 p-0"
                  onClick={handleClearSearch}
                >
                  <X className="h-4 w-4" />
                  <span className="sr-only">{t("clear_search")}</span>
                </Button>
              )}
            </div>

            {/* Action Buttons - Stack on mobile, row on desktop */}
            <div className="grid grid-cols-2 gap-2 sm:flex sm:gap-2">
              {/* Sort Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="h-10 sm:h-11 gap-1 sm:gap-2 text-xs sm:text-sm">
                    <Filter className="h-4 w-4" />
                    <span className="hidden xs:inline">{t("sort_by")}</span>
                    <span className="font-medium hidden sm:inline">
                      {sortBy === "name" ? t("name") : sortBy === "questions" ? t("question_count") : t("recent")}
                    </span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-40 sm:w-48">
                  <DropdownMenuItem
                    onClick={() => setSortBy("name")}
                    className={cn(sortBy === "name" && "bg-primary/10 font-medium")}
                  >
                    {sortBy === "name" && <CheckCircle2 className="h-4 w-4 mr-2 text-primary" />}
                    {t("name")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => setSortBy("questions")}
                    className={cn(sortBy === "questions" && "bg-primary/10 font-medium")}
                  >
                    {sortBy === "questions" && <CheckCircle2 className="h-4 w-4 mr-2 text-primary" />}
                    {t("question_count")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => setSortBy("recent")}
                    className={cn(sortBy === "recent" && "bg-primary/10 font-medium")}
                  >
                    {sortBy === "recent" && <CheckCircle2 className="h-4 w-4 mr-2 text-primary" />}
                    {t("recent")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Sort Direction */}
              <CustomTooltip
                content={
                  sortDirection === "asc"
                    ? t("sort_ascending")
                    : t("sort_descending")
                }
              >
                <Button
                  variant="outline"
                  size="icon"
                  className="h-10 w-10 sm:h-11 sm:w-11"
                  onClick={toggleSortDirection}
                >
                  {sortDirection === "asc" ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
                  <span className="sr-only">{sortDirection === "asc" ? t("ascending") : t("descending")}</span>
                </Button>
              </CustomTooltip>

              {/* Add by Code Button */}
              <Button
                variant="outline"
                className="h-10 sm:h-11 gap-1 sm:gap-2 text-xs sm:text-sm col-span-2 sm:col-span-1"
                onClick={() => setShowAddByCodeModal(true)}
              >
                <Download className="h-4 w-4" />
                <span>{t("add_by_code")}</span>
              </Button>

              {/* Manage Shares Button */}
              <Button
                variant="outline"
                className="h-10 sm:h-11 gap-1 sm:gap-2 text-xs sm:text-sm col-span-2 sm:col-span-1"
                onClick={() => setShowManageSharesModal(true)}
              >
                <Users className="h-4 w-4" />
                <span className="hidden xs:inline">{t("manage_shares")}</span>
                <span className="xs:hidden">{t("manage_shared_exams")}</span>
              </Button>

              {/* Create Button */}
              <CustomTooltip content={t("create_new_exam_tooltip")}>
                <EditExamDialog
                  exam={{
                    id: 0,
                    user_id: 0, // NAPRAWIONE: dodane user_id
                    name: "",
                    description: "",
                    created_at: "",
                    questions: []
                  }}
                  onSave={handleSave}
                  trigger={
                    <Button className="h-10 sm:h-11 gap-1 sm:gap-2 text-xs sm:text-sm">
                      <PlusCircle className="h-4 w-4" />
                      <span className="hidden sm:inline">{t("create")}</span>
                      <span className="sm:hidden">Create</span>
                    </Button>
                  }
                />
              </CustomTooltip>
            </div>
          </motion.div>

          {/* Results count */}
          {searchQuery && (
            <div className="mb-4 text-xs sm:text-sm text-muted-foreground px-1">
              {filteredExams.length === 0
                ? t("no_results_found")
                : t("showing_results", { count: filteredExams.length, total: exams.length })}
            </div>
          )}

          {/* Exams grid - Mobile First Grid */}
          {filteredExams.length === 0 && searchQuery ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                <Search className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
              <h3 className="text-base sm:text-lg font-medium mb-2 text-center">{t("no_matching_exams")}</h3>
              <p className="text-muted-foreground text-center max-w-md mb-6 text-sm sm:text-base px-4">
                {t("try_different_search")}
              </p>
              <Button variant="outline" onClick={handleClearSearch} className="h-10 sm:h-11">
                {t("clear_search")}
              </Button>
            </div>
          ) : (
            <motion.div
              className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-6"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              <AnimatePresence>
                {filteredExams.map((exam) => (
                  <motion.div
                    key={exam.id}
                    variants={itemVariants}
                    layout
                    exit={{ opacity: 0, scale: 0.8 }}
                    className="group"
                  >
                    <Card className="flex flex-col h-full overflow-hidden border-border/60 bg-card/95 backdrop-blur-sm hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 hover:-translate-y-1">
                      <CardHeader className="pb-2 sm:pb-3 flex flex-row items-start justify-between space-y-0 p-4 sm:p-6">
                        <div className="space-y-1 sm:space-y-1.5 flex-1 min-w-0 pr-2">
                          <div className="flex items-start gap-2 flex-wrap">
                            <CardTitle className="text-lg sm:text-xl font-bold line-clamp-2 leading-tight">
                              {exam.name}
                            </CardTitle>
                            <div className="flex gap-1 flex-wrap">
                              {exam.access_type === 'shared' && (
                                <Badge variant="secondary" className="text-xs flex items-center gap-1 h-5">
                                  <Download className="h-3 w-3" />
                                  {t("imported")}
                                </Badge>
                              )}
                              {exam.is_shared && exam.access_type !== 'shared' && (
                                <Badge variant="outline" className="text-xs flex items-center gap-1 h-5">
                                  <Share2 className="h-3 w-3" />
                                  {t("shared")}
                                </Badge>
                              )}
                            </div>
                          </div>
                          <CardDescription className="line-clamp-2 text-xs sm:text-sm">
                            {exam.description || t("no_description")}
                          </CardDescription>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 flex-shrink-0">
                              <MoreHorizontal className="h-4 w-4" />
                              <span className="sr-only">{t("options")}</span>
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-44 sm:w-48">
                            {exam.access_type !== 'shared' && (
                              <>
                                <EditExamDialog
                                  exam={exam}
                                  onSave={handleSave}
                                  trigger={
                                    <DropdownMenuItem onSelect={(e) => e.preventDefault()} className="text-sm">
                                      <Edit className="h-4 w-4 mr-2" />
                                      {t("edit")}
                                    </DropdownMenuItem>
                                  }
                                />
                                <DropdownMenuItem onSelect={() => handleShare(exam.id)} className="text-sm">
                                  <Share2 className="h-4 w-4 mr-2" />
                                  {t("share_exam")}
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                              </>
                            )}
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive text-sm"
                              onSelect={() => {
                                if (exam.access_type === 'shared') {
                                  handleRemoveSharedExam(exam.id)
                                } else {
                                  handleDelete(exam.id)
                                }
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {exam.access_type === 'shared' ? t("remove_from_library") : t("delete")}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </CardHeader>

                      <CardContent className="pb-2 sm:pb-3 flex-grow p-4 sm:p-6 pt-0">
                        <p className="text-xs sm:text-sm text-muted-foreground line-clamp-2 mb-3 sm:mb-4">
                          {exam.description || t("no_description")}
                        </p>

                        <div className="flex flex-wrap gap-1.5 sm:gap-2 mt-auto">
                          <Badge variant="secondary" className="flex items-center gap-1 text-xs h-5 sm:h-6">
                            <Target className="h-3 w-3" />
                            {exam.questions.length} {t("questions")}
                          </Badge>

                          {exam.conversation_id && exam.conversation_id > 0 && (
                            <Badge variant="outline" className="flex items-center gap-1 text-xs h-5 sm:h-6">
                              <Clock className="h-3 w-3" />
                              {t("last_taken")}
                            </Badge>
                          )}

                          {exam.created_at && (
                            <Badge variant="outline" className="flex items-center gap-1 text-xs h-5 sm:h-6">
                              <span className="truncate">{formatDate(exam.created_at)}</span>
                            </Badge>
                          )}
                        </div>
                      </CardContent>

                      <CardFooter className="pt-2 sm:pt-3 flex justify-end p-4 sm:p-6">
                        <CustomTooltip content={t("start_exam_session")}>
                          <Button
                            variant="default"
                            className="w-full transition-all duration-300 group-hover:bg-primary/90 h-9 sm:h-10 text-sm sm:text-base"
                            onClick={() => handleStudy(exam)}
                          >
                            {t("study")}
                            <ChevronRight className="h-4 w-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
                          </Button>
                        </CustomTooltip>
                      </CardFooter>
                    </Card>
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </>
      )}

      {/* Add by Code Modal - Mobile Responsive */}
      {showAddByCodeModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm p-4 sm:p-0">
          <div className="fixed left-4 right-4 top-1/2 -translate-y-1/2 sm:left-[50%] sm:right-auto sm:top-[50%] sm:translate-x-[-50%] sm:translate-y-[-50%] bg-background p-4 sm:p-6 shadow-lg rounded-lg border max-w-md sm:w-full">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">{t("add_exam_by_code")}</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowAddByCodeModal(false)
                  setShareCodeInput("")
                  setShareCodeInfo(null)
                }}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              {t("add_exam_by_code_description")}
            </p>

            <div className="space-y-4">
              <div className="space-y-2">
                <Input
                  value={shareCodeInput}
                  onChange={(e) => {
                    const value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '')
                    if (value.length <= 12) {
                      setShareCodeInput(value)
                    }
                  }}
                  placeholder={t("enter_12_character_code")}
                  className="font-mono text-center tracking-widest text-base sm:text-lg h-12 sm:h-14"
                  maxLength={12}
                />
                {shareCodeInput.length > 0 && shareCodeInput.length < 12 && (
                  <p className="text-sm text-muted-foreground">
                    {t("code_length_requirement", { current: shareCodeInput.length, required: 12 })}
                  </p>
                )}
                {shareCodeInput.length === 12 && (
                  <p className="text-sm text-green-600">
                    ✓ {t("valid_code_format")}
                  </p>
                )}
              </div>

              {shareCodeInfoLoading && (
                <Card className="border-muted">
                  <CardContent className="flex items-center justify-center p-4 sm:p-6">
                    <div className="flex items-center gap-3">
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary"></div>
                      <span className="text-sm text-muted-foreground">{t("loading_exam_information")}</span>
                    </div>
                  </CardContent>
                </Card>
              )}

              {shareCodeInfo && (
                <Card className="border-primary/20">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base sm:text-lg">{shareCodeInfo.exam_name}</CardTitle>
                    <CardDescription className="text-sm">
                      {shareCodeInfo.question_count} {t("questions")}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pb-3">
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {shareCodeInfo.exam_description || t("no_description")}
                    </p>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {t("shared_date_downloads", {
                        date: formatDate(shareCodeInfo.created_at),
                        downloads: shareCodeInfo.access_count
                      })}
                    </div>
                    {shareCodeInfo.already_added && (
                      <Badge variant="secondary" className="mt-2">
                        {t("already_in_library")}
                      </Badge>
                    )}
                    {shareCodeInfo.is_own_exam && (
                      <Badge variant="outline" className="mt-2">
                        {t("your_own_exam")}
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              )}

              {shareCodeInput.length === 12 && !shareCodeInfoLoading && !shareCodeInfo && (
                <Card className="border-destructive/20">
                  <CardContent className="flex items-center justify-center p-4">
                    <p className="text-sm text-destructive">
                      {t("invalid_or_expired_share_code")}
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>

            <div className="flex flex-col sm:flex-row justify-end gap-2 mt-6">
              <Button
                variant="outline"
                className="w-full sm:w-auto h-10 sm:h-11"
                onClick={() => {
                  setShowAddByCodeModal(false)
                  setShareCodeInput("")
                  setShareCodeInfo(null)
                }}
              >
                {t("cancel")}
              </Button>
              <Button
                onClick={handleAddByCode}
                disabled={!shareCodeInfo || shareCodeInfo.already_added || shareCodeInfo.is_own_exam}
                className="w-full sm:w-auto h-10 sm:h-11"
              >
                {shareCodeInfo?.already_added
                  ? t("already_added")
                  : shareCodeInfo?.is_own_exam
                  ? t("your_own_exam")
                  : t("add_to_library")
                }
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Manage Shares Modal - Mobile Responsive */}
      {showManageSharesModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm">
          <div className="fixed inset-x-0 bottom-0 sm:right-0 sm:inset-x-auto sm:top-0 h-[85vh] sm:h-full w-full sm:w-[90vw] md:w-[540px] bg-background shadow-lg border-t sm:border-l sm:border-t-0 overflow-y-auto">
            <div className="p-4 sm:p-6">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-lg font-semibold">{t("manage_shared_exams")}</h2>
                  <p className="text-sm text-muted-foreground">
                    {t("manage_share_codes_and_statistics")}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowManageSharesModal(false)}
                  className="h-8 w-8 p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <Tabs defaultValue="codes" className="mt-6">
                <TabsList className="grid w-full grid-cols-2 h-10">
                  <TabsTrigger value="codes" className="text-sm">{t("my_codes")}</TabsTrigger>
                  <TabsTrigger value="stats" className="text-sm">{t("statistics")}</TabsTrigger>
                </TabsList>

                <TabsContent value="codes" className="space-y-3 mt-4">
                  <div className="space-y-3">
                    {myCodes.length === 0 ? (
                      <div className="text-center py-8">
                        <Share2 className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground mb-4" />
                        <p className="text-sm text-muted-foreground">{t("no_share_codes_created")}</p>
                      </div>
                    ) : (
                      myCodes.map((code) => (
                        <Card key={code.share_code}>
                          <CardContent className="p-3 sm:p-4">
                            <div className="flex justify-between items-start">
                              <div className="flex-1 pr-2">
                                <h4 className="font-medium text-card-foreground text-sm sm:text-base line-clamp-1">
                                  {code.content_name}
                                </h4>
                                <p className="text-xs sm:text-sm text-muted-foreground">
                                  {code.item_count} {t("questions")} • {code.access_count} {t("downloads")}
                                </p>
                                <p className="text-xs text-muted-foreground mt-1">
                                  {t("created")} {formatDate(code.created_at)}
                                </p>
                                <div className="flex items-center gap-2 mt-2">
                                  <code className="text-xs bg-muted px-2 py-1 rounded font-mono select-all">
                                    {code.share_code}
                                  </code>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={(e) => handleCopyCode(code.share_code, e)}
                                    className="h-6 w-6 p-0 hover:bg-muted relative z-20"
                                    title={t("copy_code")}
                                  >
                                    <Copy className="h-3 w-3" />
                                  </Button>
                                </div>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  e.preventDefault()
                                  handleDeactivateCode(code.share_code)
                                }}
                                className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 w-8 p-0 flex-shrink-0 relative z-20"
                                title={t("deactivate_code")}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="stats" className="space-y-3 mt-4">
                  {shareStats ? (
                    <div className="grid gap-3 sm:gap-4">
                      <Card>
                        <CardContent className="p-3 sm:p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                              <Share2 className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
                            </div>
                            <div>
                              <p className="text-xl sm:text-2xl font-bold">{shareStats.created_share_codes}</p>
                              <p className="text-xs sm:text-sm text-muted-foreground">{t("share_codes_created")}</p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="p-3 sm:p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                              <Download className="h-4 w-4 sm:h-5 sm:w-5 text-blue-500" />
                            </div>
                            <div>
                              <p className="text-xl sm:text-2xl font-bold">{shareStats.added_shared_exams}</p>
                              <p className="text-xs sm:text-sm text-muted-foreground">{t("imported_exams")}</p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="p-3 sm:p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                              <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
                            </div>
                            <div>
                              <p className="text-xl sm:text-2xl font-bold">{shareStats.total_exam_accesses}</p>
                              <p className="text-xs sm:text-sm text-muted-foreground">{t("total_downloads_of_your_exams")}</p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <TrendingUp className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground mb-4" />
                      <p className="text-sm text-muted-foreground">{t("loading_statistics")}</p>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
