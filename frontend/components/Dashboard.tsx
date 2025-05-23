"use client"

import type React from "react"
import { useEffect, useState, useContext, useMemo, useCallback } from "react"
import Link from "next/link"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from "recharts"
import {
  ChevronDown,
  ChevronUp,
  BookOpen,
  TestTube,
  Calendar,
  TrendingUp,
  Clock,
  Target,
  Award,
  BarChart3,
  Activity,
  RefreshCw,
  Filter,
  X,
} from "lucide-react"
import { AuthContext } from "@/contexts/AuthContext"
import { useTranslation } from "react-i18next"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"

// --- Types ---
type DateString = string

interface ExamResult {
  id: number
  exam_id: number
  exam_name: string
  user_id: number
  started_at: DateString
  completed_at: DateString | null
  score: number
}

interface StudyRecord {
  id: number
  session_id: number | null
  user_flashcard_id: number | null
  rating: number
  reviewed_at: DateString
}

interface StudySession {
  id: number
  user_id: number
  deck_id: number
  started_at: DateString
  completed_at: DateString | null
}

interface UserFlashcard {
  id: number
  user_id: number
  flashcard_id: number
  ef: number
  interval: number
  repetitions: number
  next_review: DateString
}

interface SessionDuration {
  date: DateString
  duration_hours: number
}

interface DashboardData {
  study_records: StudyRecord[]
  user_flashcards: UserFlashcard[]
  study_sessions: StudySession[]
  exam_results: ExamResult[]
  session_durations: SessionDuration[]
  exam_daily_average: {
    date: DateString
    average_score: number
  }[]
  flashcard_daily_average: {
    date: DateString
    average_rating: number
  }[]
  deck_names: Record<number, string>
}

// --- Helpers ---
const sortByDateAscending = <T extends { date: string }>(data: T[]): T[] =>
  [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

const CHART_COLORS = {
  primary: "hsl(var(--primary))",
  secondary: "hsl(var(--secondary))",
  accent: "hsl(var(--accent))",
  success: "#10b981",
  warning: "#f59e0b",
  error: "#ef4444",
  info: "#3b82f6",
}

interface CustomTooltipPayload {
  name?: string
  value?: number | string
  color?: string
}

interface CustomTooltipProps {
  active?: boolean
  payload?: CustomTooltipPayload[]
  label?: string
}

// Custom components
const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <Card className="bg-popover/95 backdrop-blur-sm border-border shadow-lg">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">{formatDate(label || "")}</CardTitle>
        </CardHeader>
        <CardContent className="py-1">
          {payload.map((item, index) => (
            <p key={index} className="text-sm flex items-center gap-2" style={{ color: item.color }}>
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
              {item.name}: <span className="font-medium">{item.value}</span>
            </p>
          ))}
        </CardContent>
      </Card>
    )
  }
  return null
}

const LoadingSpinner = ({ progress }: { progress: number }) => {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <Activity className="h-12 w-12 mx-auto text-primary animate-pulse" />
          <h2 className="text-2xl font-semibold text-foreground">{t("loadingData")}</h2>
          <p className="text-muted-foreground">{t("preparingDashboard")}</p>
        </div>
        <div className="space-y-2">
          <Progress value={progress} className="h-2" />
          <p className="text-center text-sm text-muted-foreground">{progress}%</p>
        </div>
      </div>
    </div>
  )
}

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  className?: string
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, trend, className }) => (
  <Card className={`hover:shadow-md transition-all duration-200 ${className}`}>
    <CardContent className="p-6">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        <div className="flex flex-col items-end space-y-2">
          <div className="p-2 bg-primary/10 rounded-lg">{icon}</div>
          {trend && (
            <Badge variant={trend.isPositive ? "success" : "destructive"} className="text-xs">
              <TrendingUp className={`h-3 w-3 mr-1 ${!trend.isPositive && "rotate-180"}`} />
              {Math.abs(trend.value)}%
            </Badge>
          )}
        </div>
      </div>
    </CardContent>
  </Card>
)

interface DateInputProps {
  id: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  label: string
}

const DateInput: React.FC<DateInputProps> = ({ id, value, onChange, label }) => {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-medium text-foreground">
        {label}
      </label>
      <div className="relative">
        <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
        <input
          id={id}
          type="date"
          value={value}
          onChange={onChange}
          className="pl-10 pr-3 py-2 w-full border border-input rounded-md bg-background text-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
        />
      </div>
    </div>
  )
}

const FilterCard: React.FC<{
  filterStartDate: string
  filterEndDate: string
  selectedExamId: number | null
  selectedDeckId: number | null
  setFilterStartDate: (date: string) => void
  setFilterEndDate: (date: string) => void
  setSelectedExamId: (id: number | null) => void
  setSelectedDeckId: (id: number | null) => void
  examOptions: { id: number; name: string }[]
  deckOptions: { id: number; name: string }[]
  onClearFilters: () => void
  hasActiveFilters: boolean
}> = ({
  filterStartDate,
  filterEndDate,
  selectedExamId,
  selectedDeckId,
  setFilterStartDate,
  setFilterEndDate,
  setSelectedExamId,
  setSelectedDeckId,
  examOptions,
  deckOptions,
  onClearFilters,
  hasActiveFilters,
}) => {
  const { t } = useTranslation()

  return (
    <Card className="mb-8 shadow-sm border-border/50">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">{t("filter.title")}</CardTitle>
          </div>
          {hasActiveFilters && (
            <Button variant="outline" size="sm" onClick={onClearFilters} className="text-xs">
              <X className="h-3 w-3 mr-1" />
              {t("filter.clearAll")}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <DateInput
            id="start-date"
            label={t("filter.dateFrom")}
            value={filterStartDate}
            onChange={(e) => setFilterStartDate(e.target.value)}
          />
          <DateInput
            id="end-date"
            label={t("filter.dateTo")}
            value={filterEndDate}
            onChange={(e) => setFilterEndDate(e.target.value)}
          />
          <div className="space-y-2">
            <label htmlFor="exam-select" className="block text-sm font-medium text-foreground">
              {t("filter.selectExam")}
            </label>
            <Select
              value={selectedExamId?.toString() ?? ""}
              onValueChange={(value) => setSelectedExamId(value && value !== "all" ? Number.parseInt(value) : null)}
            >
              <SelectTrigger id="exam-select">
                <SelectValue placeholder={t("filter.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t("filter.all")}</SelectItem>
                {examOptions.map(({ id, name }) => (
                  <SelectItem key={id} value={id.toString()}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label htmlFor="deck-select" className="block text-sm font-medium text-foreground">
              {t("filter.selectDeck")}
            </label>
            <Select
              value={selectedDeckId?.toString() ?? ""}
              onValueChange={(value) => setSelectedDeckId(value && value !== "all" ? Number.parseInt(value) : null)}
            >
              <SelectTrigger id="deck-select">
                <SelectValue placeholder={t("filter.all")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t("filter.all")}</SelectItem>
                {deckOptions.map(({ id, name }) => (
                  <SelectItem key={id} value={id.toString()}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

const CookbookSection = () => {
  const { t } = useTranslation()
  return (
    <Card className="shadow-sm border-border/50">
      <CardHeader>
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <CardTitle>{t("cookbookTitle")}</CardTitle>
        </div>
        <CardDescription>{t("cookbookIntro")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Target className="h-4 w-4" />
            {t("cookbook.flashcardsLimit")}
          </h3>
          <p className="text-muted-foreground">{t("cookbook.flashcardsLimitInfo")}</p>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            {t("cookbook.promptInstructions")}
          </h3>
          <p className="text-muted-foreground">{t("cookbook.promptIntro")}</p>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">{t("cookbook.example1Title")}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm italic text-muted-foreground">
                  &#34;Please generate 40 flashcards for studying before the computer networks exam, using the file I
                  uploaded earlier.&#34;
                </p>
              </CardContent>
            </Card>

            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">{t("cookbook.example2Title")}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm italic text-muted-foreground">
                  &#34;Please create an exam for studying before the computer networks exam consisting of 30 questions,
                  using the file I uploaded earlier.&#34;
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <h4 className="font-medium flex items-center gap-2">
              <Activity className="h-4 w-4" />
              {t("cookbook.chatUseExplanation")}
            </h4>
            <p className="text-sm text-muted-foreground">{t("cookbook.chatUseExplanationInfo")}</p>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium flex items-center gap-2">
              <Clock className="h-4 w-4" />
              {t("cookbook.waitTimeExplanation")}
            </h4>
            <p className="text-sm text-muted-foreground">{t("cookbook.waitTimeExplanationInfo")}</p>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              {t("cookbook.progressTracking")}
            </h4>
            <p className="text-sm text-muted-foreground">{t("cookbook.progressTrackingInfo")}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// --- Main Component Dashboard ---
const Dashboard: React.FC = () => {
  const { t } = useTranslation()
  const { isAuthenticated } = useContext(AuthContext)
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [progress, setProgress] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [filterStartDate, setFilterStartDate] = useState<string>("")
  const [filterEndDate, setFilterEndDate] = useState<string>("")
  const [selectedExamId, setSelectedExamId] = useState<number | null>(null)
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null)

  // UI state for collapsible sections
  const [isExamAnalysisOpen, setIsExamAnalysisOpen] = useState<boolean>(true)
  const [isFlashcardAnalysisOpen, setIsFlashcardAnalysisOpen] = useState<boolean>(true)

  const hasActiveFilters = useMemo(() => {
    return !!(filterStartDate || filterEndDate || selectedExamId || selectedDeckId)
  }, [filterStartDate, filterEndDate, selectedExamId, selectedDeckId])

  const clearAllFilters = useCallback(() => {
    setFilterStartDate("")
    setFilterEndDate("")
    setSelectedExamId(null)
    setSelectedDeckId(null)
  }, [])

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        setProgress(10)

        if (!isAuthenticated) {
          throw new Error(t("pleaseLogin"))
        }

        const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"

        setProgress(30)
        const response = await fetch(`${API_BASE_URL}/dashboard/`, {
          credentials: "include",
        })

        setProgress(70)

        if (!response.ok) {
          throw new Error(t("fetchError", { statusText: response.statusText }))
        }

        const result: DashboardData = await response.json()
        setData(result)
        setProgress(100)
      } catch (err: unknown) {
        console.error("Error fetching dashboard data:", err)
        setError(err instanceof Error ? err.message : t("fetchErrorGeneric"))
        setProgress(100)
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [isAuthenticated, t])

  // Deck options
  const deckOptions = useMemo(() => {
    if (!data) return []
    return Object.entries(data.deck_names).map(([id, name]) => ({
      id: Number.parseInt(id, 10),
      name,
    }))
  }, [data])

  // Exam options
  const examOptions = useMemo(() => {
    if (!data) return []
    const uniqueExamsMap = new Map<number, string>()
    data.exam_results.forEach((exam) => {
      if (!uniqueExamsMap.has(exam.exam_id)) {
        uniqueExamsMap.set(exam.exam_id, exam.exam_name || `${t("filter.selectExam")} ${exam.exam_id}`)
      }
    })
    return Array.from(uniqueExamsMap, ([id, name]) => ({ id, name }))
  }, [data, t])

  // Data filtering and processing
  const filteredData = useMemo(() => {
    if (!data) return null

    let filteredStudySessions = data.study_sessions
    let filteredStudyRecords = data.study_records
    let filteredExamResults = data.exam_results
    let filteredExamDailyAverage = data.exam_daily_average
    let filteredFlashcardDailyAverage = data.flashcard_daily_average
    let filteredSessionDurations = data.session_durations
    let filteredUserFlashcards = data.user_flashcards

    if (filterStartDate || filterEndDate) {
      const start = filterStartDate ? new Date(filterStartDate) : null
      const end = filterEndDate ? new Date(filterEndDate) : null

      filteredStudySessions = filteredStudySessions.filter((session) => {
        const sessionStartDate = new Date(session.started_at)
        if (start && sessionStartDate < start) return false
        if (end && sessionStartDate > end) return false
        return true
      })

      filteredStudyRecords = filteredStudyRecords.filter((record) => {
        const recordDate = new Date(record.reviewed_at)
        if (start && recordDate < start) return false
        if (end && recordDate > end) return false
        if (record.session_id === null) return false
        const session = filteredStudySessions.find((s) => s.id === record.session_id)
        return session !== undefined
      })

      filteredExamResults = filteredExamResults.filter((exam) => {
        const examDate = new Date(exam.started_at)
        if (start && examDate < start) return false
        if (end && examDate > end) return false
        return true
      })

      filteredExamDailyAverage = filteredExamDailyAverage.filter((avg) => {
        const avgDate = new Date(avg.date)
        if (start && avgDate < start) return false
        if (end && avgDate > end) return false
        return true
      })

      const flashcardRatingsMap = new Map<string, { total: number; count: number }>()
      filteredStudyRecords.forEach((record) => {
        if (record.reviewed_at && record.rating !== null) {
          const date = record.reviewed_at.split("T")[0]
          if (!flashcardRatingsMap.has(date)) {
            flashcardRatingsMap.set(date, { total: 0, count: 0 })
          }
          const entry = flashcardRatingsMap.get(date)!
          entry.total += record.rating
          entry.count += 1
        }
      })
      filteredFlashcardDailyAverage = Array.from(flashcardRatingsMap.entries()).map(([date, { total, count }]) => ({
        date,
        average_rating: count > 0 ? Number.parseFloat((total / count).toFixed(2)) : 0,
      }))

      const relevantSessionDates = new Set(filteredStudySessions.map((s) => s.started_at.split("T")[0]))
      filteredSessionDurations = filteredSessionDurations.filter((dur) => relevantSessionDates.has(dur.date))
    }

    if (selectedExamId) {
      filteredExamResults = filteredExamResults.filter((exam) => exam.exam_id === selectedExamId)
    }

    if (selectedDeckId) {
      filteredStudySessions = filteredStudySessions.filter((session) => session.deck_id === selectedDeckId)
      const sessionIds = new Set(filteredStudySessions.map((s) => s.id))
      filteredStudyRecords = filteredStudyRecords.filter(
        (record) => record.session_id !== null && sessionIds.has(record.session_id),
      )
    }

    const userFlashcardIds = new Set(
      filteredStudyRecords.map((r) => r.user_flashcard_id).filter((id) => id !== null) as number[],
    )
    filteredUserFlashcards = data.user_flashcards.filter((card) => userFlashcardIds.has(card.id))

    return {
      ...data,
      study_sessions: filteredStudySessions,
      study_records: filteredStudyRecords,
      exam_results: filteredExamResults,
      exam_daily_average: filteredExamDailyAverage,
      flashcard_daily_average: filteredFlashcardDailyAverage,
      session_durations: filteredSessionDurations,
      user_flashcards: filteredUserFlashcards,
    }
  }, [data, filterStartDate, filterEndDate, selectedExamId, selectedDeckId])

  // Summary statistics
  const summaryStats = useMemo(() => {
    if (!filteredData) return null

    const totalStudyTime = filteredData.session_durations.reduce((acc, session) => acc + session.duration_hours, 0)
    const averageExamScore =
      filteredData.exam_results.length > 0
        ? filteredData.exam_results.reduce((acc, exam) => acc + exam.score, 0) / filteredData.exam_results.length
        : 0
    const totalFlashcards = filteredData.study_records.length

    // Correctly calculate the study streak
    const calculateStudyStreak = (): number => {
      if (filteredData.study_sessions.length === 0) return 0

      // Get unique study session dates (without time)
      const studyDates = Array.from(
        new Set(
          filteredData.study_sessions.map(session => {
            return new Date(session.started_at).toISOString().split('T')[0]
          })
        )
      ).sort((a, b) => new Date(b).getTime() - new Date(a).getTime()) // Sort from newest to oldest

      if (studyDates.length === 0) return 0

      // Check if there was a study session today or yesterday
      const today = new Date()
      const todayString = today.toISOString().split('T')[0]
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)
      const yesterdayString = yesterday.toISOString().split('T')[0]

      // If the last session was neither today nor yesterday, streak is 0
      const lastStudyDate = studyDates[0]
      if (lastStudyDate !== todayString && lastStudyDate !== yesterdayString) {
        return 0
      }

      // Calculate streak by checking consecutive days backwards
      let streak = 0
      // eslint-disable-next-line prefer-const
      let currentDate = new Date(lastStudyDate)

      for (const studyDate of studyDates) {
        const currentDateString = currentDate.toISOString().split('T')[0]
        if (studyDate === currentDateString) {
          streak++
          // Move the date back by one day
          currentDate.setDate(currentDate.getDate() - 1)
        } else {
          // If continuity is broken, stop
          break
        }
      }

      return streak
    }

    const studyStreak = calculateStudyStreak()

    return {
      totalStudyTime: totalStudyTime.toFixed(1),
      averageExamScore: averageExamScore.toFixed(1),
      totalFlashcards,
      studyStreak,
    }
  }, [filteredData])

  // Chart data processing
  const examLineChartData = useMemo(() => {
    if (!filteredData) return []
    return sortByDateAscending(
      filteredData.exam_daily_average.map((record) => ({
        date: record.date,
        average_score: record.average_score,
      })),
    )
  }, [filteredData])

  const examStudyTimeData = useMemo(() => {
    if (!filteredData) return []
    const studyTimeMap = new Map<string, number>()
    filteredData.exam_results
      .filter((exam) => exam.started_at && exam.completed_at)
      .forEach((exam) => {
        const start = new Date(exam.started_at)
        const end = new Date(exam.completed_at!)
        const duration = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
        const date = start.toISOString().split("T")[0]
        studyTimeMap.set(date, (studyTimeMap.get(date) || 0) + Number.parseFloat(duration.toFixed(2)))
      })
    return sortByDateAscending(
      Array.from(studyTimeMap.entries()).map(([date, study_time]) => ({
        date,
        study_time: Number.parseFloat(study_time.toFixed(2)),
      })),
    )
  }, [filteredData])

  const histogramExamResultsData = useMemo(() => {
    if (!filteredData) return []
    const buckets = Array.from({ length: 11 }, (_, i) => ({
      score: i < 10 ? `${i * 10}-${i * 10 + 9}` : "100",
      count: 0,
      percentage: 0,
    }))

    filteredData.exam_results.forEach((exam) => {
      if (exam.score === 100) {
        buckets[10].count += 1
      } else {
        const bucketIndex = Math.floor(exam.score / 10)
        if (bucketIndex >= 0 && bucketIndex < 10) {
          buckets[bucketIndex].count += 1
        }
      }
    })

    const total = filteredData.exam_results.length
    buckets.forEach((bucket) => {
      bucket.percentage = total > 0 ? Math.round((bucket.count / total) * 100) : 0
    })

    return buckets
  }, [filteredData])

  const flashcardLineChartData = useMemo(() => {
    if (!filteredData) return []
    return sortByDateAscending(
      filteredData.flashcard_daily_average.map((record) => ({
        date: record.date,
        average_rating: record.average_rating,
      })),
    )
  }, [filteredData])

  const totalStudyTimeData = useMemo(() => {
    if (!filteredData) return []
    const studyTimeMap = new Map<string, number>()
    filteredData.study_sessions.forEach((session) => {
      const sessionDate = session.started_at.split("T")[0]
      const durationRecord = filteredData.session_durations.find((d) => d.date === sessionDate)
      if (durationRecord) {
        studyTimeMap.set(sessionDate, (studyTimeMap.get(sessionDate) || 0) + durationRecord.duration_hours)
      }
    })
    return sortByDateAscending(
      Array.from(studyTimeMap.entries()).map(([date, total_study_time]) => ({
        date,
        total_study_time: Number.parseFloat(total_study_time.toFixed(2)),
      })),
    )
  }, [filteredData])

  const flashcardsByHourData = useMemo(() => {
    if (!filteredData) return []
    const hourMap = new Map<number, number>()
    filteredData.study_records.forEach((record) => {
      if (!record.reviewed_at) return
      const hour = new Date(record.reviewed_at).getHours()
      hourMap.set(hour, (hourMap.get(hour) || 0) + 1)
    })
    return Array.from(hourMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([hour, count]) => ({
        hour: `${hour}:00`,
        count,
        hourNum: hour,
      }))
  }, [filteredData])

  const flashcardRatingDistribution = useMemo(() => {
    if (!filteredData) return []
    const ratingMap = new Map<number, number>()
    filteredData.study_records.forEach((record) => {
      ratingMap.set(record.rating, (ratingMap.get(record.rating) || 0) + 1)
    })

    const ratingLabels = {
      0: "Hard",
      3: "Good",
      5: "Easy",
    }

    return Array.from(ratingMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([rating, count]) => ({
        rating: ratingLabels[rating as keyof typeof ratingLabels] || `Rating ${rating}`,
        count,
        percentage: Math.round((count / filteredData.study_records.length) * 100),
      }))
  }, [filteredData])

  if (loading) {
    return <LoadingSpinner progress={progress} />
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen p-8">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-2">
              <X className="h-5 w-5" />
              {t("error")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={() => window.location.reload()} className="w-full">
              <RefreshCw className="h-4 w-4 mr-2" />
              {t("retry")}
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  if (!filteredData) {
    return (
      <div className="flex items-center justify-center min-h-screen p-8">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{t("noData")}</CardTitle>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 lg:p-6 space-y-8 max-w-7xl">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl lg:text-4xl font-bold text-primary">{t("dashboardTitle")}</h1>
        <p className="text-muted-foreground">{t("dashboardSubtitle")}</p>
      </div>

      {/* Summary Statistics */}
      {summaryStats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          <StatCard
            title={t("totalStudyTime")}
            value={`${summaryStats.totalStudyTime}h`}
            subtitle={t("thisMonth")}
            icon={<Clock className="h-5 w-5 text-primary" />}
            trend={{ value: 12, isPositive: true }}
          />
          <StatCard
            title={t("averageExamScore")}
            value={`${summaryStats.averageExamScore}%`}
            subtitle={t("allExams")}
            icon={<Award className="h-5 w-5 text-primary" />}
            trend={{ value: 8, isPositive: true }}
          />
          <StatCard
            title={t("flashcardsStudied")}
            value={summaryStats.totalFlashcards}
            subtitle={t("totalCards")}
            icon={<BookOpen className="h-5 w-5 text-primary" />}
            trend={{ value: 15, isPositive: true }}
          />
          <StatCard
            title={t("studyStreak")}
            value={`${summaryStats.studyStreak} days`}
            subtitle={t("keepItUp")}
            icon={<TrendingUp className="h-5 w-5 text-primary" />}
            trend={{ value: 3, isPositive: true }}
          />
        </div>
      )}

      {/* Filters */}
      <FilterCard
        filterStartDate={filterStartDate}
        filterEndDate={filterEndDate}
        selectedExamId={selectedExamId}
        selectedDeckId={selectedDeckId}
        setFilterStartDate={setFilterStartDate}
        setFilterEndDate={setFilterEndDate}
        setSelectedExamId={setSelectedExamId}
        setSelectedDeckId={setSelectedDeckId}
        examOptions={examOptions}
        deckOptions={deckOptions}
        onClearFilters={clearAllFilters}
        hasActiveFilters={hasActiveFilters}
      />

      {/* Exam Analysis Section */}
      <Card className="shadow-sm border-border/50">
        <button type="button" onClick={() => setIsExamAnalysisOpen(!isExamAnalysisOpen)} className="w-full text-left">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 hover:bg-muted/50 transition-colors duration-200 rounded-t-lg">
            <CardTitle className="text-xl lg:text-2xl font-bold flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <TestTube className="h-5 w-5 lg:h-6 lg:w-6 text-primary" />
              </div>
              {t("examAnalysis")}
            </CardTitle>
            {isExamAnalysisOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </CardHeader>
        </button>

        {isExamAnalysisOpen && (
          <CardContent className="pt-0">
            {filteredData.exam_results.length === 0 ? (
              <Card className="border-dashed">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TestTube className="h-5 w-5" />
                    {t("noExams.title")}
                  </CardTitle>
                  <CardDescription>{t("noExams.description")}</CardDescription>
                </CardHeader>
                <CardFooter>
                  <Button asChild>
                    <Link href="/tests">{t("noExams.addExam")}</Link>
                  </Button>
                </CardFooter>
              </Card>
            ) : (
              <div className="grid gap-6 lg:gap-8">
                {/* Exam Score Trend */}
                <div className="space-y-4">
                  <h4 className="text-lg font-semibold flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    {t("averageExamScoresOverTime")}
                  </h4>
                  <div className="h-64 lg:h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={examLineChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="date" tickFormatter={formatDate} stroke="hsl(var(--muted-foreground))" />
                        <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="average_score"
                          name={t("average_score")}
                          stroke={CHART_COLORS.primary}
                          strokeWidth={3}
                          dot={{ fill: CHART_COLORS.primary, strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: CHART_COLORS.primary, strokeWidth: 2 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Exam Score Distribution */}
                <div className="grid lg:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="text-lg font-semibold flex items-center gap-2">
                      <BarChart3 className="h-4 w-4" />
                      {t("examScoreDistribution")}
                    </h4>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={histogramExamResultsData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis dataKey="score" stroke="hsl(var(--muted-foreground))" />
                          <YAxis stroke="hsl(var(--muted-foreground))" />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar dataKey="count" name={t("count")} fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="text-lg font-semibold flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      {t("timeSpentStudyingExams")}
                    </h4>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={examStudyTimeData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis dataKey="date" tickFormatter={formatDate} stroke="hsl(var(--muted-foreground))" />
                          <YAxis stroke="hsl(var(--muted-foreground))" />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar
                            dataKey="study_time"
                            name={t("study_time")}
                            fill={CHART_COLORS.secondary}
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* Flashcard Analysis Section */}
      <Card className="shadow-sm border-border/50">
        <button
          type="button"
          onClick={() => setIsFlashcardAnalysisOpen(!isFlashcardAnalysisOpen)}
          className="w-full text-left"
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 hover:bg-muted/50 transition-colors duration-200 rounded-t-lg">
            <CardTitle className="text-xl lg:text-2xl font-bold flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <BookOpen className="h-5 w-5 lg:h-6 lg:w-6 text-primary" />
              </div>
              {t("flashcardAnalysis")}
            </CardTitle>
            {isFlashcardAnalysisOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </CardHeader>
        </button>

        {isFlashcardAnalysisOpen && (
          <CardContent className="pt-0">
            {filteredData.user_flashcards.length === 0 ? (
              <Card className="border-dashed">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5" />
                    {t("noFlashcards.title")}
                  </CardTitle>
                  <CardDescription>{t("noFlashcards.description")}</CardDescription>
                </CardHeader>
                <CardFooter>
                  <Button asChild>
                    <Link href="/flashcards">{t("noFlashcards.addFlashcards")}</Link>
                  </Button>
                </CardFooter>
              </Card>
            ) : (
              <div className="grid gap-6 lg:gap-8">
                {/* Flashcard Rating Trend */}
                <div className="space-y-4">
                  <h4 className="text-lg font-semibold flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    {t("averageFlashcardRatingsOverTime")}
                  </h4>
                  <div className="h-64 lg:h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={flashcardLineChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="date" tickFormatter={formatDate} stroke="hsl(var(--muted-foreground))" />
                        <YAxis domain={[0, 5]} stroke="hsl(var(--muted-foreground))" />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="average_rating"
                          name={t("average_rating")}
                          stroke={CHART_COLORS.success}
                          strokeWidth={3}
                          dot={{ fill: CHART_COLORS.success, strokeWidth: 2, r: 4 }}
                          activeDot={{ r: 6, stroke: CHART_COLORS.success, strokeWidth: 2 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Study Time and Activity Patterns */}
                <div className="grid lg:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="text-lg font-semibold flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      {t("totalTimeStudyingFlashcards")}
                    </h4>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={totalStudyTimeData}>
                          <defs>
                            <linearGradient id="colorStudyTime" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8} />
                              <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.1} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis dataKey="date" tickFormatter={formatDate} stroke="hsl(var(--muted-foreground))" />
                          <YAxis stroke="hsl(var(--muted-foreground))" />
                          <Tooltip content={<CustomTooltip />} />
                          <Area
                            type="monotone"
                            dataKey="total_study_time"
                            name={t("total_study_time")}
                            stroke={CHART_COLORS.primary}
                            fill="url(#colorStudyTime)"
                            strokeWidth={2}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="text-lg font-semibold flex items-center gap-2">
                      <Activity className="h-4 w-4" />
                      {t("flashcardsSolvedByHour")}
                    </h4>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={flashcardsByHourData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis dataKey="hour" stroke="hsl(var(--muted-foreground))" />
                          <YAxis stroke="hsl(var(--muted-foreground))" />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar dataKey="count" name={t("count")} fill={CHART_COLORS.info} radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Flashcard Rating Distribution */}
                <div className="space-y-4">
                  <h4 className="text-lg font-semibold flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    {t("flashcardDifficultyDistribution")}
                  </h4>
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={flashcardRatingDistribution}
                            cx="50%"
                            cy="50%"
                            outerRadius={80}
                            dataKey="count"
                            nameKey="rating"
                          >
                            {flashcardRatingDistribution.map((entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={
                                  [CHART_COLORS.error, CHART_COLORS.warning, CHART_COLORS.success][index] ||
                                  CHART_COLORS.primary
                                }
                              />
                            ))}
                          </Pie>
                          <Tooltip content={<CustomTooltip />} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="space-y-3">
                      {flashcardRatingDistribution.map((item, index) => (
                        <div key={item.rating} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <div
                              className="w-4 h-4 rounded-full"
                              style={{
                                backgroundColor:
                                  [CHART_COLORS.error, CHART_COLORS.warning, CHART_COLORS.success][index] ||
                                  CHART_COLORS.primary,
                              }}
                            />
                            <span className="font-medium">{item.rating}</span>
                          </div>
                          <div className="text-right">
                            <div className="font-semibold">{item.count}</div>
                            <div className="text-sm text-muted-foreground">{item.percentage}%</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* Cookbook Section */}
      <CookbookSection />
    </div>
  )
}

export default Dashboard