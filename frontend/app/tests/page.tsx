"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
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
} from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { StudyExam } from "@/components/StudyExam"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"
import type { Exam } from "@/types"

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
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
}

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

  const { t } = useTranslation()
  const searchInputRef = useRef<HTMLInputElement>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"
  const EXAMS_API_BASE = `${API_BASE_URL}/exams/`
  const CONVERSATIONS_URL = `${API_BASE_URL}/chats/`

  const fetchExams = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(EXAMS_API_BASE, {
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

      if (!exam.conversation_id || exam.conversation_id === 0) {
        const convRes = await fetch(CONVERSATIONS_URL, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ exam_id: exam.id, title: exam.name }),
        })
        if (!convRes.ok) {
          const convErr = await convRes.json()
          let errorMsg = "Failed to create conversation."
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
          throw new Error(fetchErr.detail || "Could not re-fetch updated exam.")
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
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="flex flex-col items-center justify-center mb-12">
          <div className="w-48 h-10 bg-muted animate-pulse rounded-md mb-4"></div>
          <div className="w-64 h-6 bg-muted animate-pulse rounded-md"></div>
        </div>

        <div className="w-full max-w-md mx-auto mb-8 bg-muted animate-pulse h-10 rounded-md"></div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="bg-muted animate-pulse rounded-xl h-64"></div>
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 flex items-center justify-center min-h-[50vh]">
        <Card className="w-full max-w-md border-destructive/20">
          <CardHeader className="pb-4">
            <CardTitle className="text-2xl font-bold text-destructive flex items-center gap-2">
              <X className="h-6 w-6" />
              {t("error")}
            </CardTitle>
            <CardDescription>{t("error_occurred")}</CardDescription>
          </CardHeader>
          <CardContent className="pb-6">
            <p className="text-destructive/90 bg-destructive/5 p-4 rounded-md border border-destructive/10">{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchExams} className="w-full">
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
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <motion.div
        className="flex flex-col items-center justify-center mb-8 md:mb-12"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent mb-2">
          {t("tests")}
        </h1>
        <p className="text-muted-foreground text-center max-w-xl mb-2">{t("tests_description")}</p>
        <CustomTooltip
          content={
            t("tests_tooltip") ||
            "Egzaminy pomagają sprawdzić wiedzę i przygotować się do testów. Twórz własne egzaminy lub importuj gotowe pytania."
          }
        >
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
            <CardHeader className="pb-4">
              <CardTitle className="text-2xl font-bold">{t("welcome_tests")}</CardTitle>
              <CardDescription>{t("get_started_create_test")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center space-y-6 py-12">
              <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center">
                <TestTube className="h-12 w-12 text-primary" />
              </div>
              <p className="text-center text-muted-foreground max-w-md">{t("no_tests_available_extended")}</p>
            </CardContent>
            <CardFooter className="flex justify-center">
              <EditExamDialog
                exam={{ id: 0, name: "", description: "", created_at: "", questions: [] }}
                onSave={handleSave}
                trigger={
                  <Button className="w-full" variant="default">
                    <PlusCircle className="h-5 w-5 mr-2" />
                    {t("create_your_first_test")}
                  </Button>
                }
              />
            </CardFooter>
          </Card>
        </motion.div>
      ) : (
        <>
          {/* Search and Filter Bar */}
          <motion.div
            className="mb-8 flex flex-col md:flex-row gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <div
              className={cn(
                "relative flex-grow transition-all duration-300 rounded-lg",
                isSearchFocused ? "ring-2 ring-primary/20" : "",
              )}
            >
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                ref={searchInputRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("search_exams")}
                className="pl-10 pr-10 h-11 bg-background/60 backdrop-blur-sm border-muted"
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

            <div className="flex gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="h-11 gap-2">
                    <Filter className="h-4 w-4" />
                    <span className="hidden sm:inline">{t("sort_by")}</span>
                    <span className="font-medium">
                      {sortBy === "name" ? t("name") : sortBy === "questions" ? t("question_count") : t("recent")}
                    </span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
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

              <CustomTooltip
                content={
                  sortDirection === "asc"
                    ? t("sort_ascending") || "Sortuj rosnąco"
                    : t("sort_descending") || "Sortuj malejąco"
                }
              >
                <Button variant="outline" size="icon" className="h-11 w-11" onClick={toggleSortDirection}>
                  {sortDirection === "asc" ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
                  <span className="sr-only">{sortDirection === "asc" ? t("ascending") : t("descending")}</span>
                </Button>
              </CustomTooltip>

              <CustomTooltip content={t("create_new_exam_tooltip") || "Utwórz nowy egzamin"}>
                <EditExamDialog
                  exam={{ id: 0, name: "", description: "", created_at: "", questions: [] }}
                  onSave={handleSave}
                  trigger={
                    <Button className="h-11 gap-2">
                      <PlusCircle className="h-4 w-4" />
                      <span className="hidden sm:inline">{t("create")}</span>
                    </Button>
                  }
                />
              </CustomTooltip>
            </div>
          </motion.div>

          {/* Results count */}
          {searchQuery && (
            <div className="mb-4 text-sm text-muted-foreground">
              {filteredExams.length === 0
                ? t("no_results_found")
                : t("showing_results", { count: filteredExams.length, total: exams.length })}
            </div>
          )}

          {/* Exams grid */}
          {filteredExams.length === 0 && searchQuery ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                <Search className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium mb-2">{t("no_matching_exams")}</h3>
              <p className="text-muted-foreground text-center max-w-md mb-6">{t("try_different_search")}</p>
              <Button variant="outline" onClick={handleClearSearch}>
                {t("clear_search")}
              </Button>
            </div>
          ) : (
            <motion.div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
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
                      <CardHeader className="pb-3 flex flex-row items-start justify-between space-y-0">
                        <div className="space-y-1.5">
                          <CardTitle className="text-xl font-bold line-clamp-1 pr-6">{exam.name}</CardTitle>
                          <CardDescription className="line-clamp-1">
                            {exam.description || t("no_description")}
                          </CardDescription>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <MoreHorizontal className="h-4 w-4" />
                              <span className="sr-only">{t("options")}</span>
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-48">
                            <EditExamDialog
                              exam={exam}
                              onSave={handleSave}
                              trigger={
                                <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                                  <Edit className="h-4 w-4 mr-2" />
                                  {t("edit")}
                                </DropdownMenuItem>
                              }
                            />
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              onSelect={() => handleDelete(exam.id)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t("delete")}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </CardHeader>

                      <CardContent className="pb-3 flex-grow">
                        <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                          {exam.description || t("no_description")}
                        </p>

                        <div className="flex flex-wrap gap-2 mt-auto">
                          <Badge variant="secondary" className="flex items-center gap-1">
                            <Target className="h-3 w-3" />
                            {exam.questions.length} {t("questions")}
                          </Badge>

                          {exam.conversation_id && exam.conversation_id > 0 && (
                            <Badge variant="outline" className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {t("last_taken")}
                            </Badge>
                          )}

                          {exam.created_at && (
                            <Badge variant="outline" className="flex items-center gap-1 text-xs">
                              {formatDate(exam.created_at)}
                            </Badge>
                          )}
                        </div>
                      </CardContent>

                      <CardFooter className="pt-3 flex justify-end">
                        <CustomTooltip
                          content={t("start_exam_session") || "Rozpocznij sesję egzaminacyjną z tym testem"}
                        >
                          <Button
                            variant="default"
                            className="w-full sm:w-auto transition-all duration-300 group-hover:bg-primary/90"
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
    </div>
  )
}
