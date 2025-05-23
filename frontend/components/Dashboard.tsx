"use client"

import React from "react"
import { useEffect, useState, useContext, useMemo, useCallback, type ErrorInfo } from "react"
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
  AlertTriangle,
  Info,
  Brain,
  CheckCircle,
  XCircle,
  Minus,
} from "lucide-react"
import { AuthContext } from "@/contexts/AuthContext"
import { useTranslation } from "react-i18next"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

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

// --- Enhanced Error Boundary ---
interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

class ChartErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Chart Error:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <Alert variant="destructive" className="m-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Chart Error</AlertTitle>
            <AlertDescription>Unable to render chart. Please try refreshing the page.</AlertDescription>
          </Alert>
        )
      )
    }

    return this.props.children
  }
}

// --- Enhanced Helpers ---
/**
 * Safely formats a date string with comprehensive error handling
 * @param dateString - The date string to format
 * @param fallback - Fallback text if date is invalid
 * @returns Formatted date string or fallback
 */
const formatDate = (dateString: string | null | undefined, fallback = "Invalid Date"): string => {
  if (!dateString || typeof dateString !== "string") {
    return fallback
  }

  try {
    const date = new Date(dateString)

    // Check if date is valid
    if (isNaN(date.getTime())) {
      return fallback
    }

    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    })
  } catch (error) {
    console.warn("Date formatting error:", error)
    return fallback
  }
}
/**
 * Validates if a date string is valid
 * @param dateString - The date string to validate
 * @returns boolean indicating if date is valid
 */
const isValidDate = (dateString: string | null | undefined): boolean => {
  if (!dateString) return false

  try {
    const date = new Date(dateString)
    return !isNaN(date.getTime())
  } catch {
    return false
  }
}

/**
 * Safely sorts data by date with validation
 */
const sortByDateAscending = <T extends { date: string }>(data: T[]): T[] => {
  if (!Array.isArray(data)) return []

  return [...data]
    .filter((item) => item && isValidDate(item.date))
    .sort((a, b) => {
      try {
        return new Date(a.date).getTime() - new Date(b.date).getTime()
      } catch {
        return 0
      }
    })
}

/**
 * Validates dashboard data structure
 */
const validateDashboardData = (data: unknown): data is DashboardData => {
  if (!data || typeof data !== "object") return false

  // Cast to Record<string, unknown> after verifying it's an object
  const dataObj = data as Record<string, unknown>

  const requiredFields = [
    "study_records",
    "user_flashcards",
    "study_sessions",
    "exam_results",
    "session_durations",
    "exam_daily_average",
    "flashcard_daily_average",
    "deck_names",
  ]

  return requiredFields.every((field) => Array.isArray(dataObj[field]) || typeof dataObj[field] === "object")
}

// --- Enhanced Color Scheme ---
const CHART_COLORS = {
  primary: "hsl(222.2 47.4% 11.2%)",
  secondary: "hsl(210 40% 98%)",
  accent: "hsl(210 40% 96%)",
  success: "#10b981",
  warning: "#f59e0b",
  error: "#ef4444",
  info: "#3b82f6",
  purple: "#8b5cf6",
  pink: "#ec4899",
  gradient: {
    primary: "linear-gradient(135deg, hsl(222.2 47.4% 11.2%) 0%, hsl(222.2 47.4% 21.2%) 100%)",
    success: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
    warning: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
    info: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
  },
}

// --- Enhanced Custom Components ---
interface CustomTooltipPayload {
  name?: string
  value?: number | string
  color?: string
  payload?: Record<string, unknown>
}

interface CustomTooltipProps {
  active?: boolean
  payload?: CustomTooltipPayload[]
  label?: string
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null

  return (
    <Card className="bg-background/95 backdrop-blur-md border-border/50 shadow-xl animate-in fade-in-0 zoom-in-95 duration-200">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-foreground">{formatDate(label, "Unknown Date")}</CardTitle>
      </CardHeader>
      <CardContent className="py-1 space-y-1">
        {payload.map((item, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full shadow-sm"
              style={{ backgroundColor: item.color }}
              aria-hidden="true"
            />
            <span className="text-muted-foreground">{item.name}:</span>
            <span className="font-semibold text-foreground">{item.value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// --- Enhanced Loading Components ---
const LoadingSpinner = ({ progress }: { progress: number }) => {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-gradient-to-br from-background via-background to-muted/20">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-4">
          <div className="relative">
            <div className="w-16 h-16 mx-auto bg-gradient-to-br from-primary/20 to-primary/5 rounded-full flex items-center justify-center">
              <Activity className="h-8 w-8 text-primary animate-pulse" />
            </div>
            <div className="absolute inset-0 w-16 h-16 mx-auto border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-foreground">{t("loadingData")}</h2>
            <p className="text-muted-foreground">{t("preparingDashboard")}</p>
          </div>
        </div>

        <div className="space-y-3">
          <Progress value={progress} className="h-3 bg-muted/50" aria-label={`Loading progress: ${progress}%`} />
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Loading...</span>
            <span className="font-medium">{progress}%</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Enhanced Stat Card ---
interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
    period?: string
  }
  className?: string
  loading?: boolean
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, trend, className, loading = false }) => {
  if (loading) {
    return (
      <Card className={`animate-pulse ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-2 flex-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-3 w-20" />
            </div>
            <Skeleton className="h-12 w-12 rounded-lg" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      className={`group hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 hover:-translate-y-1 border-border/50 bg-gradient-to-br from-card via-card to-card/50 ${className}`}
    >
      <CardContent className="p-4 items">
        <div className="flex items-center justify-between">
          <div className="space-y-2 flex-1">
            <p className="text-sm font-medium text-muted-foreground group-hover:text-muted-foreground/80 transition-colors">
              {title}
            </p>
            <p className="text-3xl font-bold text-foreground group-hover:text-primary transition-colors">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground/80">{subtitle}</p>}
          </div>
          <div className="flex flex-col items-end space-y-3">
            <div className="p-3 bg-gradient-to-br from-primary/10 to-primary/5 rounded-xl group-hover:from-primary/15 group-hover:to-primary/10 transition-all duration-300">
              {icon}
            </div>
            {trend && (
              <Badge
                variant={trend.isPositive ? "default" : "destructive"}
                className={`text-xs font-bold px-2 py-1 ${
                  trend.isPositive
                    ? "bg-gradient-to-r from-green-400/10 to-green-600/10 text-green-700 dark:text-green-600 border-green-200 dark:border-green-800"
                    : "bg-gradient-to-r from-red-500/10 to-red-600/10 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800"
                }`}
              >
                <TrendingUp className={`h-3 w-3 mr-1 ${!trend.isPositive && "rotate-180"}`} />
                {Math.abs(trend.value)}%{trend.period && <span className="ml-1 opacity-75">{trend.period}</span>}
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// --- Enhanced Date Input ---
interface DateInputProps {
  id: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  label: string
  error?: string
}

const DateInput: React.FC<DateInputProps> = ({ id, value, onChange, label, error }) => {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-medium text-foreground">
        {label}
      </label>
      <div className="relative">
        <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4 pointer-events-none" />
        <input
          id={id}
          type="date"
          value={value}
          onChange={onChange}
          className={`pl-10 pr-3 py-2 w-full border rounded-md bg-background text-foreground transition-all duration-200 focus:ring-2 focus:ring-ring focus:border-ring hover:border-border/80 ${
            error ? "border-destructive focus:ring-destructive" : "border-input"
          }`}
          aria-describedby={error ? `${id}-error` : undefined}
          aria-invalid={!!error}
        />
      </div>
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />
          {error}
        </p>
      )}
    </div>
  )
}

// --- Enhanced Filter Card ---
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
  isExpanded: boolean
  onToggleExpanded: () => void
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
  isExpanded,
  onToggleExpanded,
}) => {
  const { t } = useTranslation()

  const validateDateRange = useCallback(() => {
    if (filterStartDate && filterEndDate) {
      const start = new Date(filterStartDate)
      const end = new Date(filterEndDate)
      return start <= end
    }
    return true
  }, [filterStartDate, filterEndDate])

  const isDateRangeValid = validateDateRange()

  return (
    <Card className="mb-8 shadow-sm border-border/50 bg-gradient-to-br from-card via-card to-muted/5 overflow-hidden">
      <button
        type="button"
        onClick={onToggleExpanded}
        className="w-full text-left focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-t-lg"
        aria-expanded={isExpanded}
        aria-controls="filter-content"
      >
        <CardHeader className="pb-4 hover:bg-muted/30 transition-colors duration-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg">
                <Filter className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  {t("filter.title")}
                  {hasActiveFilters && (
                    <Badge variant="secondary" className="text-xs">
                      {[filterStartDate, filterEndDate, selectedExamId, selectedDeckId].filter(Boolean).length} active
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription className="text-sm">
                  {isExpanded ? "Click to collapse filters" : "Click to expand filters"}
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {hasActiveFilters && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation()
                    onClearFilters()
                  }}
                  className="text-xs hover:bg-destructive/10 hover:text-destructive hover:border-destructive/20"
                >
                  <X className="h-3 w-3 mr-1" />
                  {t("filter.clearAll")}
                </Button>
              )}
              {isExpanded ? (
                <ChevronUp className="h-5 w-5 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              )}
            </div>
          </div>
        </CardHeader>
      </button>

      <div
        id="filter-content"
        className={`transition-all duration-300 ease-in-out ${
          isExpanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
        } overflow-hidden`}
      >
        <CardContent className="pt-0 pb-6">
          {!isDateRangeValid && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Invalid Date Range</AlertTitle>
              <AlertDescription>The start date must be before or equal to the end date.</AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <DateInput
              id="start-date"
              label={t("filter.dateFrom")}
              value={filterStartDate}
              onChange={(e) => setFilterStartDate(e.target.value)}
              error={!isDateRangeValid ? "Invalid range" : undefined}
            />
            <DateInput
              id="end-date"
              label={t("filter.dateTo")}
              value={filterEndDate}
              onChange={(e) => setFilterEndDate(e.target.value)}
              error={!isDateRangeValid ? "Invalid range" : undefined}
            />

            <div className="space-y-2">
              <label htmlFor="exam-select" className="block text-sm font-medium text-foreground">
                {t("filter.selectExam")}
              </label>
              <Select
                value={selectedExamId?.toString() ?? ""}
                onValueChange={(value) => setSelectedExamId(value && value !== "all" ? Number.parseInt(value) : null)}
              >
                <SelectTrigger id="exam-select" className="hover:border-border/80 transition-colors">
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
                <SelectTrigger id="deck-select" className="hover:border-border/80 transition-colors">
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
      </div>
    </Card>
  )
}

// --- Enhanced Empty State ---
interface EmptyStateProps {
  icon: React.ReactNode
  title: string
  description: string
  actionLabel: string
  actionHref: string
  className?: string
}

const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, actionLabel, actionHref, className }) => (
  <Card className={`border-dashed border-2 border-border/50 bg-gradient-to-br from-muted/20 to-muted/5 ${className}`}>
    <CardContent className="flex flex-col items-center justify-center py-12 px-6 text-center">
      <div className="w-16 h-16 bg-gradient-to-br from-muted/30 to-muted/10 rounded-full flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-muted-foreground mb-6 max-w-md">{description}</p>
      <Button asChild className="bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary">
        <Link href={actionHref}>{actionLabel}</Link>
      </Button>
    </CardContent>
  </Card>
)

// --- Enhanced Cookbook Section ---
const CookbookSection = () => {
  const { t } = useTranslation()
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <Card className="shadow-sm border-border/50 bg-gradient-to-br from-card via-card to-muted/5 overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-t-lg"
        aria-expanded={isExpanded}
      >
        <CardHeader className="hover:bg-muted/30 transition-colors duration-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg">
                <BookOpen className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-xl">{t("cookbookTitle")}</CardTitle>
                <CardDescription>{t("cookbookIntro")}</CardDescription>
              </div>
            </div>
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
        </CardHeader>
      </button>

      <div
        className={`transition-all duration-300 ease-in-out ${
          isExpanded ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0"
        } overflow-hidden`}
      >
        <CardContent className="space-y-8 pb-8">
          <Alert className="border-info/20 bg-info/5">
            <Info className="h-4 w-4 text-info" />
            <AlertTitle className="text-info">Pro Tip</AlertTitle>
            <AlertDescription>{t("cookbook.flashcardsLimitInfo")}</AlertDescription>
          </Alert>

          <div className="space-y-6">
            <div className="space-y-3">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Target className="h-5 w-5 text-primary" />
                {t("cookbook.promptInstructions")}
              </h3>
              <p className="text-muted-foreground leading-relaxed">{t("cookbook.promptIntro")}</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="border-border/50 bg-gradient-to-br from-success/5 to-success/10 border-success/20">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-success" />
                    {t("cookbook.example1Title")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <blockquote className="text-sm italic text-muted-foreground border-l-4 border-success/30 pl-4">
                    &#34;Please generate 40 flashcards for studying before the computer networks exam, using the file I
                    uploaded earlier.&#34;
                  </blockquote>
                </CardContent>
              </Card>

              <Card className="border-border/50 bg-gradient-to-br from-info/5 to-info/10 border-info/20">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <TestTube className="h-4 w-4 text-info" />
                    {t("cookbook.example2Title")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <blockquote className="text-sm italic text-muted-foreground border-l-4 border-info/30 pl-4">
                    &#34;Please create an exam for studying before the computer networks exam consisting of 30 questions,
                    using the file I uploaded earlier.&#34;
                  </blockquote>
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <div className="space-y-3 p-4 rounded-lg bg-gradient-to-br from-purple/5 to-purple/10 border border-purple/20">
              <h4 className="font-medium flex items-center gap-2">
                <Brain className="h-4 w-4 text-purple" />
                {t("cookbook.chatUseExplanation")}
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed">{t("cookbook.chatUseExplanationInfo")}</p>
            </div>

            <div className="space-y-3 p-4 rounded-lg bg-gradient-to-br from-warning/5 to-warning/10 border border-warning/20">
              <h4 className="font-medium flex items-center gap-2">
                <Clock className="h-4 w-4 text-warning" />
                {t("cookbook.waitTimeExplanation")}
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed">{t("cookbook.waitTimeExplanationInfo")}</p>
            </div>

            <div className="space-y-3 p-4 rounded-lg bg-gradient-to-br from-success/5 to-success/10 border border-success/20">
              <h4 className="font-medium flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-success" />
                {t("cookbook.progressTracking")}
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed">{t("cookbook.progressTrackingInfo")}</p>
            </div>
          </div>
        </CardContent>
      </div>
    </Card>
  )
}

// --- Main Enhanced Dashboard Component ---
const EnhancedDashboard: React.FC = () => {
  const { t } = useTranslation()
  const { isAuthenticated } = useContext(AuthContext)
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [progress, setProgress] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)

  // Enhanced UI state
  const [isFilterExpanded, setIsFilterExpanded] = useState(false)
  const [isExamAnalysisOpen, setIsExamAnalysisOpen] = useState<boolean>(true)
  const [isFlashcardAnalysisOpen, setIsFlashcardAnalysisOpen] = useState<boolean>(true)
// Filters with validation
  const [filterStartDate, setFilterStartDate] = useState<string>("")
  const [filterEndDate, setFilterEndDate] = useState<string>("")
  const [selectedExamId, setSelectedExamId] = useState<number | null>(null)
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null)

  // Enhanced filter validation
  const hasActiveFilters = useMemo(() => {
    return !!(filterStartDate || filterEndDate || selectedExamId || selectedDeckId)
  }, [filterStartDate, filterEndDate, selectedExamId, selectedDeckId])

  const clearAllFilters = useCallback(() => {
    setFilterStartDate("")
    setFilterEndDate("")
    setSelectedExamId(null)
    setSelectedDeckId(null)
  }, [])

  // Enhanced data fetching with better error handling
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        setError(null)
        setProgress(10)

        if (!isAuthenticated) {
          throw new Error(t("pleaseLogin"))
        }

        const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"

        setProgress(30)

        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout

        const response = await fetch(`${API_BASE_URL}/dashboard/`, {
          credentials: "include",
          signal: controller.signal,
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
        })

        clearTimeout(timeoutId)
        setProgress(70)

        if (!response.ok) {
          throw new Error(t("fetchError", { statusText: response.statusText }))
        }

        const result = await response.json()

        // Validate data structure
        if (!validateDashboardData(result)) {
          throw new Error("Invalid data structure received from server")
        }

        setData(result)
        setProgress(100)
      } catch (err: unknown) {
        console.error("Error fetching dashboard data:", err)

        if (err instanceof Error) {
          if (err.name === "AbortError") {
            setError("Request timed out. Please try again.")
          } else {
            setError(err.message)
          }
        } else {
          setError(t("fetchErrorGeneric"))
        }
        setProgress(100)
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [isAuthenticated, t])

  // Enhanced data processing with validation
  const deckOptions = useMemo(() => {
    if (!data?.deck_names) return []

    try {
      return Object.entries(data.deck_names)
        .filter(([id, name]) => id && name)
        .map(([id, name]) => ({
          id: Number.parseInt(id, 10),
          name: String(name),
        }))
        .filter((option) => !isNaN(option.id))
    } catch (error) {
      console.warn("Error processing deck options:", error)
      return []
    }
  }, [data])

  const examOptions = useMemo(() => {
    if (!data?.exam_results) return []

    try {
      const uniqueExamsMap = new Map<number, string>()

      data.exam_results
        .filter((exam) => exam && typeof exam.exam_id === "number")
        .forEach((exam) => {
          if (!uniqueExamsMap.has(exam.exam_id)) {
            const name = exam.exam_name || `${t("filter.selectExam")} ${exam.exam_id}`
            uniqueExamsMap.set(exam.exam_id, name)
          }
        })

      return Array.from(uniqueExamsMap, ([id, name]) => ({ id, name }))
    } catch (error) {
      console.warn("Error processing exam options:", error)
      return []
    }
  }, [data, t])

  // Enhanced data filtering with comprehensive validation
  const filteredData = useMemo(() => {
    if (!data) return null

    try {
      let filteredStudySessions = [...(data.study_sessions || [])]
      let filteredStudyRecords = [...(data.study_records || [])]
      let filteredExamResults = [...(data.exam_results || [])]
      let filteredExamDailyAverage = [...(data.exam_daily_average || [])]
      let filteredFlashcardDailyAverage = [...(data.flashcard_daily_average || [])]
      let filteredSessionDurations = [...(data.session_durations || [])]
      let filteredUserFlashcards = [...(data.user_flashcards || [])]

      // Date range filtering with validation
      if (filterStartDate || filterEndDate) {
        const start = filterStartDate && isValidDate(filterStartDate) ? new Date(filterStartDate) : null
        const end = filterEndDate && isValidDate(filterEndDate) ? new Date(filterEndDate) : null

        if (start || end) {
          filteredStudySessions = filteredStudySessions.filter((session) => {
            if (!session?.started_at || !isValidDate(session.started_at)) return false

            const sessionStartDate = new Date(session.started_at)
            if (start && sessionStartDate < start) return false
            if (end && sessionStartDate > end) return false
            return true
          })

          filteredStudyRecords = filteredStudyRecords.filter((record) => {
            if (!record?.reviewed_at || !isValidDate(record.reviewed_at)) return false

            const recordDate = new Date(record.reviewed_at)
            if (start && recordDate < start) return false
            if (end && recordDate > end) return false
            if (record.session_id === null) return false

            const session = filteredStudySessions.find((s) => s.id === record.session_id)
            return session !== undefined
          })

          filteredExamResults = filteredExamResults.filter((exam) => {
            if (!exam?.started_at || !isValidDate(exam.started_at)) return false

            const examDate = new Date(exam.started_at)
            if (start && examDate < start) return false
            if (end && examDate > end) return false
            return true
          })

          filteredExamDailyAverage = filteredExamDailyAverage.filter((avg) => {
            if (!avg?.date || !isValidDate(avg.date)) return false

            const avgDate = new Date(avg.date)
            if (start && avgDate < start) return false
            if (end && avgDate > end) return false
            return true
          })

          // Recalculate flashcard daily averages
          const flashcardRatingsMap = new Map<string, { total: number; count: number }>()
          filteredStudyRecords.forEach((record) => {
            if (record?.reviewed_at && isValidDate(record.reviewed_at) && typeof record.rating === "number") {
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

          const relevantSessionDates = new Set(
            filteredStudySessions
              .filter((s) => s?.started_at && isValidDate(s.started_at))
              .map((s) => s.started_at.split("T")[0]),
          )
          filteredSessionDurations = filteredSessionDurations.filter(
            (dur) => dur?.date && relevantSessionDates.has(dur.date),
          )
        }
      }

      // Exam filtering
      if (selectedExamId && typeof selectedExamId === "number") {
        filteredExamResults = filteredExamResults.filter((exam) => exam?.exam_id === selectedExamId)
      }

      // Deck filtering
      if (selectedDeckId && typeof selectedDeckId === "number") {
        filteredStudySessions = filteredStudySessions.filter((session) => session?.deck_id === selectedDeckId)
        const sessionIds = new Set(filteredStudySessions.map((s) => s.id))
        filteredStudyRecords = filteredStudyRecords.filter(
          (record) => record?.session_id !== null && sessionIds.has(record.session_id),
        )
      }

      // Filter user flashcards based on study records
      const userFlashcardIds = new Set(
        filteredStudyRecords.map((r) => r?.user_flashcard_id).filter((id): id is number => typeof id === "number"),
      )
      filteredUserFlashcards = data.user_flashcards.filter((card) => card && userFlashcardIds.has(card.id))

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
    } catch (error) {
      console.error("Error filtering data:", error)
      return data // Return original data if filtering fails
    }
  }, [data, filterStartDate, filterEndDate, selectedExamId, selectedDeckId])

  // Enhanced summary statistics with validation
  const summaryStats = useMemo(() => {
    if (!filteredData) return null

    try {
      const totalStudyTime = (filteredData.session_durations || [])
        .filter((session) => session && typeof session.duration_hours === "number")
        .reduce((acc, session) => acc + session.duration_hours, 0)

      const validExamResults = (filteredData.exam_results || []).filter(
        (exam) => exam && typeof exam.score === "number" && !isNaN(exam.score),
      )

      const averageExamScore =
        validExamResults.length > 0
          ? validExamResults.reduce((acc, exam) => acc + exam.score, 0) / validExamResults.length
          : 0

      const totalFlashcards = (filteredData.study_records || []).length

      // Enhanced study streak calculation with validation
      const calculateStudyStreak = (): number => {
        const validSessions = (filteredData.study_sessions || []).filter(
          (session) => session?.started_at && isValidDate(session.started_at),
        )

        if (validSessions.length === 0) return 0

        try {
          const studyDates = Array.from(
            new Set(
              validSessions.map((session) => {
                return new Date(session.started_at).toISOString().split("T")[0]
              }),
            ),
          ).sort((a, b) => new Date(b).getTime() - new Date(a).getTime())

          if (studyDates.length === 0) return 0

          const today = new Date()
          const todayString = today.toISOString().split("T")[0]
          const yesterday = new Date(today)
          yesterday.setDate(yesterday.getDate() - 1)
          const yesterdayString = yesterday.toISOString().split("T")[0]

          const lastStudyDate = studyDates[0]
          if (lastStudyDate !== todayString && lastStudyDate !== yesterdayString) {
            return 0
          }

          let streak = 0
          const currentDate = new Date(lastStudyDate)

          for (const studyDate of studyDates) {
            const currentDateString = currentDate.toISOString().split("T")[0]
            if (studyDate === currentDateString) {
              streak++
              currentDate.setDate(currentDate.getDate() - 1)
            } else {
              break
            }
          }

          return streak
        } catch (error) {
          console.warn("Error calculating study streak:", error)
          return 0
        }
      }

      const studyStreak = calculateStudyStreak()

      return {
        totalStudyTime: totalStudyTime.toFixed(1),
        averageExamScore: averageExamScore.toFixed(1),
        totalFlashcards,
        studyStreak,
      }
    } catch (error) {
      console.error("Error calculating summary stats:", error)
      return {
        totalStudyTime: "0.0",
        averageExamScore: "0.0",
        totalFlashcards: 0,
        studyStreak: 0,
      }
    }
  }, [filteredData])

  // Enhanced chart data processing with error handling
  const examLineChartData = useMemo(() => {
    if (!filteredData?.exam_daily_average) return []

    try {
      return sortByDateAscending(
        filteredData.exam_daily_average
          .filter((record) => record && isValidDate(record.date) && typeof record.average_score === "number")
          .map((record) => ({
            date: record.date,
            average_score: Number.parseFloat(record.average_score.toFixed(2)),
          })),
      )
    } catch (error) {
      console.warn("Error processing exam line chart data:", error)
      return []
    }
  }, [filteredData])

  const examStudyTimeData = useMemo(() => {
    if (!filteredData?.exam_results) return []

    try {
      const studyTimeMap = new Map<string, number>()

      filteredData.exam_results
        .filter(
          (exam) =>
            exam &&
            exam.started_at &&
            exam.completed_at &&
            isValidDate(exam.started_at) &&
            isValidDate(exam.completed_at),
        )
        .forEach((exam) => {
          try {
            const start = new Date(exam.started_at)
            const end = new Date(exam.completed_at!)
            const duration = (end.getTime() - start.getTime()) / (1000 * 60 * 60)

            if (duration >= 0 && duration < 24) {
              // Sanity check: less than 24 hours
              const date = start.toISOString().split("T")[0]
              studyTimeMap.set(date, (studyTimeMap.get(date) || 0) + duration)
            }
          } catch (error) {
            console.warn("Error processing exam duration:", error)
          }
        })

      return sortByDateAscending(
        Array.from(studyTimeMap.entries()).map(([date, study_time]) => ({
          date,
          study_time: Number.parseFloat(study_time.toFixed(2)),
        })),
      )
    } catch (error) {
      console.warn("Error processing exam study time data:", error)
      return []
    }
  }, [filteredData])

  const histogramExamResultsData = useMemo(() => {
    if (!filteredData?.exam_results) return []

    try {
      const buckets = Array.from({ length: 11 }, (_, i) => ({
        score: i < 10 ? `${i * 10}-${i * 10 + 9}` : "100",
        count: 0,
        percentage: 0,
      }))

      const validExamResults = filteredData.exam_results.filter(
        (exam) => exam && typeof exam.score === "number" && exam.score >= 0 && exam.score <= 100,
      )

      validExamResults.forEach((exam) => {
        if (exam.score === 100) {
          buckets[10].count += 1
        } else {
          const bucketIndex = Math.floor(exam.score / 10)
          if (bucketIndex >= 0 && bucketIndex < 10) {
            buckets[bucketIndex].count += 1
          }
        }
      })

      const total = validExamResults.length
      buckets.forEach((bucket) => {
        bucket.percentage = total > 0 ? Math.round((bucket.count / total) * 100) : 0
      })

      return buckets
    } catch (error) {
      console.warn("Error processing histogram data:", error)
      return []
    }
  }, [filteredData])

  const flashcardLineChartData = useMemo(() => {
    if (!filteredData?.flashcard_daily_average) return []

    try {
      return sortByDateAscending(
        filteredData.flashcard_daily_average
          .filter((record) => record && isValidDate(record.date) && typeof record.average_rating === "number")
          .map((record) => ({
            date: record.date,
            average_rating: Number.parseFloat(record.average_rating.toFixed(2)),
          })),
      )
    } catch (error) {
      console.warn("Error processing flashcard line chart data:", error)
      return []
    }
  }, [filteredData])

  const totalStudyTimeData = useMemo(() => {
    if (!filteredData?.study_sessions || !filteredData?.session_durations) return []

    try {
      const studyTimeMap = new Map<string, number>()

      filteredData.study_sessions
        .filter((session) => session?.started_at && isValidDate(session.started_at))
        .forEach((session) => {
          const sessionDate = session.started_at.split("T")[0]
          const durationRecord = filteredData.session_durations.find((d) => d?.date === sessionDate)

          if (durationRecord && typeof durationRecord.duration_hours === "number") {
            studyTimeMap.set(sessionDate, (studyTimeMap.get(sessionDate) || 0) + durationRecord.duration_hours)
          }
        })

      return sortByDateAscending(
        Array.from(studyTimeMap.entries()).map(([date, total_study_time]) => ({
          date,
          total_study_time: Number.parseFloat(total_study_time.toFixed(2)),
        })),
      )
    } catch (error) {
      console.warn("Error processing total study time data:", error)
      return []
    }
  }, [filteredData])

  const flashcardsByHourData = useMemo(() => {
    if (!filteredData?.study_records) return []

    try {
      const hourMap = new Map<number, number>()

      filteredData.study_records
        .filter((record) => record?.reviewed_at && isValidDate(record.reviewed_at))
        .forEach((record) => {
          try {
            const hour = new Date(record.reviewed_at).getHours()
            if (hour >= 0 && hour <= 23) {
              hourMap.set(hour, (hourMap.get(hour) || 0) + 1)
            }
          } catch (error) {
            console.warn("Error processing record hour:", error)
          }
        })

      return Array.from(hourMap.entries())
        .sort((a, b) => a[0] - b[0])
        .map(([hour, count]) => ({
          hour: `${hour.toString().padStart(2, "0")}:00`,
          count,
          hourNum: hour,
        }))
    } catch (error) {
      console.warn("Error processing flashcards by hour data:", error)
      return []
    }
  }, [filteredData])

  const flashcardRatingDistribution = useMemo(() => {
    if (!filteredData?.study_records) return []

    try {
      const ratingMap = new Map<number, number>()
      const validRecords = filteredData.study_records.filter((record) => record && typeof record.rating === "number")

      validRecords.forEach((record) => {
        ratingMap.set(record.rating, (ratingMap.get(record.rating) || 0) + 1)
      })

      const ratingLabels: Record<number, string> = {
        0: "Hard",
        3: "Good",
        5: "Easy",
      }

      return Array.from(ratingMap.entries())
        .sort((a, b) => a[0] - b[0])
        .map(([rating, count]) => ({
          rating: ratingLabels[rating] || `Rating ${rating}`,
          count,
          percentage: validRecords.length > 0 ? Math.round((count / validRecords.length) * 100) : 0,
        }))
    } catch (error) {
      console.warn("Error processing flashcard rating distribution:", error)
      return []
    }
  }, [filteredData])

  // Loading state
  if (loading) {
    return <LoadingSpinner progress={progress} />
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen p-8 bg-gradient-to-br from-background via-background to-muted/20">
        <Card className="w-full max-w-md shadow-xl border-destructive/20">
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              {t("error")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground leading-relaxed">{error}</p>
          </CardContent>
          <CardFooter>
            <Button
              onClick={() => window.location.reload()}
              className="w-full bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              {t("retry")}
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  // No data state
  if (!filteredData) {
    return (
      <div className="flex items-center justify-center min-h-screen p-8 bg-gradient-to-br from-background via-background to-muted/20">
        <EmptyState
          icon={<BarChart3 className="h-8 w-8 text-muted-foreground" />}
          title={t("noData")}
          description="No dashboard data available. Please check your connection and try again."
          actionLabel="Refresh"
          actionHref="/"
        />
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 lg:p-6 space-y-8 max-w-7xl bg-gradient-to-br from-background via-background to-muted/10 min-h-screen">
      {/* Enhanced Header */}
      <div className="text-center space-y-4 py-8">
        <div className="inline-flex items-center gap-3 px-6 py-3">
          <BarChart3 className="h-6 w-6 text-primary" />
          <h1 className="text-3xl lg:text-4xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
            {t("dashboardTitle")}
          </h1>
        </div>
        <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">{t("dashboardSubtitle")}</p>
      </div>

      {/* Enhanced Summary Statistics */}
      {summaryStats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          <StatCard
            title={t("totalStudyTime")}
            value={`${summaryStats.totalStudyTime}h`}
            subtitle={t("thisMonth")}
            icon={<Clock className="h-5 w-5 text-primary" />}
            trend={{ value: 12, isPositive: true, period: "vs last month" }}
            loading={loading}
          />
          <StatCard
            title={t("averageExamScore")}
            value={`${summaryStats.averageExamScore}%`}
            subtitle={t("allExams")}
            icon={<Award className="h-5 w-5 text-primary" />}
            trend={{ value: 8, isPositive: true, period: "improvement" }}
            loading={loading}
          />
          <StatCard
            title={t("flashcardsStudied")}
            value={summaryStats.totalFlashcards}
            subtitle={t("totalCards")}
            icon={<BookOpen className="h-5 w-5 text-primary" />}
            trend={{ value: 15, isPositive: true, period: "this week" }}
            loading={loading}
          />
          <StatCard
            title={t("studyStreak")}
            value={`${summaryStats.studyStreak} days`}
            subtitle={t("keepItUp")}
            icon={<TrendingUp className="h-5 w-5 text-primary" />}
            trend={{ value: 3, isPositive: true, period: "personal best" }}
            loading={loading}
          />
        </div>
      )}

      {/* Enhanced Filters */}
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
        isExpanded={isFilterExpanded}
        onToggleExpanded={() => setIsFilterExpanded(!isFilterExpanded)}
      />

      {/* Enhanced Exam Analysis Section */}
      <Card className="shadow-lg border-border/50 bg-gradient-to-br from-card via-card to-muted/5 overflow-hidden">
        <button
          type="button"
          onClick={() => setIsExamAnalysisOpen(!isExamAnalysisOpen)}
          className="w-full text-left focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-t-lg"
          aria-expanded={isExamAnalysisOpen}
          aria-controls="exam-analysis-content"
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 hover:bg-muted/30 transition-all duration-200 rounded-t-lg">
            <CardTitle className="text-xl lg:text-2xl font-bold flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-primary/10 to-primary/5 rounded-xl">
                <TestTube className="h-5 w-5 lg:h-6 lg:w-6 text-primary" />
              </div>
              <div>
                <span>{t("examAnalysis")}</span>
                <div className="text-sm font-normal text-muted-foreground mt-1">
                  {filteredData.exam_results.length} exams analyzed
                </div>
              </div>
            </CardTitle>
            <div className="flex items-center gap-2">
              {filteredData.exam_results.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {filteredData.exam_results.length} results
                </Badge>
              )}
              {isExamAnalysisOpen ? (
                <ChevronUp className="h-5 w-5 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              )}
            </div>
          </CardHeader>
        </button>

        <div
          id="exam-analysis-content"
          className={`transition-all duration-300 ease-in-out ${
            isExamAnalysisOpen ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"
          } overflow-hidden`}
        >
          <CardContent className="pt-0 pb-8">
            {filteredData.exam_results.length === 0 ? (
              <EmptyState
                icon={<TestTube className="h-8 w-8 text-muted-foreground" />}
                title={t("noExams.title")}
                description={t("noExams.description")}
                actionLabel={t("noExams.addExam")}
                actionHref="/tests"
              />
            ) : (
              <div className="grid gap-8 lg:gap-10">
                {/* Exam Score Trend */}
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-semibold flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-primary" />
                      {t("averageExamScoresOverTime")}
                    </h4>
                    <Badge variant="outline" className="text-xs">
                      {examLineChartData.length} data points
                    </Badge>
                  </div>

                  <ChartErrorBoundary>
                    <div className="h-80 lg:h-96 p-4 bg-gradient-to-br from-muted/20 to-muted/5 rounded-xl border border-border/30">
                      {examLineChartData.length === 0 ? (
                        <div className="flex items-center justify-center h-full">
                          <div className="text-center space-y-2">
                            <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto" />
                            <p className="text-muted-foreground">No exam data available for the selected period</p>
                          </div>
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={examLineChartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                            <defs>
                              <linearGradient id="examScoreGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.5} />
                                <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                            <XAxis
                              dataKey="date"
                              stroke="hsl(var(--muted-foreground))"
                              fontSize={12}
                            />
                            <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend />
                            <Area
                              type="monotone"
                              dataKey="average_score"
                              stroke={CHART_COLORS.primary}
                              fill={CHART_COLORS.gradient.primary}
                              strokeWidth={1}
                            />
                            <Line
                              type="monotone"
                              dataKey="average_score"
                              name={t("average_score")}
                              stroke="hsl(var(--muted-foreground))"
                              strokeWidth={3}
                              dot={{ fill: CHART_COLORS.primary, strokeWidth: 2, r: 5 }}
                              activeDot={{ r: 7, stroke: CHART_COLORS.primary, strokeWidth: 3, fill: "white" }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </ChartErrorBoundary>
                </div>

                {/* Exam Score Distribution and Study Time */}
                <div className="grid lg:grid-cols-2 gap-8">
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h4 className="text-lg font-semibold flex items-center gap-2">
                        <BarChart3 className="h-5 w-5 text-primary" />
                        {t("examScoreDistribution")}
                      </h4>
                      <Badge variant="outline" className="text-xs">
                        {filteredData.exam_results.length} exams
                      </Badge>
                    </div>

                    <ChartErrorBoundary>
                      <div className="h-80 p-4 bg-gradient-to-br from-muted/20 to-muted/5 rounded-xl border border-border/30">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={histogramExamResultsData}
                            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                          >
                            <defs>
                              <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8} />
                                <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.6} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                            <XAxis dataKey="score" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                            <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="count" name={t("count")} fill="hsl(var(--muted-foreground))" radius={[6, 6, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </ChartErrorBoundary>
                  </div>

                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h4 className="text-lg font-semibold flex items-center gap-2">
                        <Clock className="h-5 w-5 text-primary" />
                        {t("timeSpentStudyingExams")}
                      </h4>
                      <Badge variant="outline" className="text-xs">
                        {examStudyTimeData.length} sessions
                      </Badge>
                    </div>

                    <ChartErrorBoundary>
                      <div className="h-80 p-4 bg-gradient-to-br from-muted/20 to-muted/5 rounded-xl border border-border/30">
                        {examStudyTimeData.length === 0 ? (
                          <div className="flex items-center justify-center h-full">
                            <div className="text-center space-y-2">
                              <Clock className="h-12 w-12 text-muted-foreground mx-auto" />
                              <p className="text-muted-foreground">No study time data available</p>
                            </div>
                          </div>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={examStudyTimeData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                              <defs>
                                <linearGradient id="timeGradient" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor={CHART_COLORS.secondary} stopOpacity={0.8} />
                                  <stop offset="95%" stopColor={CHART_COLORS.secondary} stopOpacity={0.6} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                              <XAxis
                                dataKey="date"
                                stroke="hsl(var(--muted-foreground))"
                                fontSize={12}
                              />
                              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                              <Tooltip content={<CustomTooltip />} />
                              <Bar
                                dataKey="study_time"
                                name={t("study_time")}
                                fill="hsl(var(--muted-foreground))"
                                radius={[6, 6, 0, 0]}
                              />
                            </BarChart>
                          </ResponsiveContainer>
                        )}
                      </div>
                    </ChartErrorBoundary>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </div>
      </Card>

      {/* Enhanced Flashcard Analysis Section */}
      <Card className="shadow-lg border-border/50 bg-gradient-to-br from-card via-card to-muted/5 overflow-hidden">
        <button
          type="button"
          onClick={() => setIsFlashcardAnalysisOpen(!isFlashcardAnalysisOpen)}
          className="w-full text-left focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-t-lg"
          aria-expanded={isFlashcardAnalysisOpen}
          aria-controls="flashcard-analysis-content"
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 hover:bg-muted/30 transition-all duration-200 rounded-t-lg">
            <CardTitle className="text-xl lg:text-2xl font-bold flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-primary/10 to-primary/5 rounded-xl">
                <BookOpen className="h-5 w-5 lg:h-6 lg:w-6 text-primary" />
              </div>
              <div>
                <span>{t("flashcardAnalysis")}</span>
                <div className="text-sm font-normal text-muted-foreground mt-1">
                  {filteredData.user_flashcards.length} flashcards tracked
                </div>
              </div>
            </CardTitle>
            <div className="flex items-center gap-2">
              {filteredData.user_flashcards.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {filteredData.study_records.length} reviews
                </Badge>
              )}
              {isFlashcardAnalysisOpen ? (
                <ChevronUp className="h-5 w-5 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              )}
            </div>
          </CardHeader>
        </button>

        <div
          id="flashcard-analysis-content"
          className={`transition-all duration-300 ease-in-out ${
            isFlashcardAnalysisOpen ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"
          } overflow-hidden`}
        >
          <CardContent className="pt-0 pb-8">
            {filteredData.user_flashcards.length === 0 ? (
              <EmptyState
                icon={<BookOpen className="h-8 w-8 text-muted-foreground" />}
                title={t("noFlashcards.title")}
                description={t("noFlashcards.description")}
                actionLabel={t("noFlashcards.addFlashcards")}
                actionHref="/flashcards"
              />
            ) : (
              <div className="grid gap-8 lg:gap-10">
                {/* Flashcard Rating Trend */}
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-semibold flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-primary" />
                      {t("averageFlashcardRatingsOverTime")}
                    </h4>
                    <Badge variant="outline" className="text-xs">
                      {flashcardLineChartData.length} data points
                    </Badge>
                  </div>

                  <ChartErrorBoundary>
                    <div className="h-80 lg:h-96 p-4 bg-gradient-to-br from-muted/20 to-muted/5 rounded-xl border border-border/30">
                      {flashcardLineChartData.length === 0 ? (
                        <div className="flex items-center justify-center h-full">
                          <div className="text-center space-y-2">
                            <BookOpen className="h-12 w-12 text-muted-foreground mx-auto" />
                            <p className="text-muted-foreground">No flashcard data available for the selected period</p>
                          </div>
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart
                            data={flashcardLineChartData}
                            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                          >
                            <defs>
                              <linearGradient id="flashcardGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={CHART_COLORS.success} stopOpacity={0.1} />
                                <stop offset="95%" stopColor={CHART_COLORS.success} stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                            <XAxis
                              dataKey="date"
                              stroke="hsl(var(--muted-foreground))"
                              fontSize={12}
                            />
                            <YAxis domain={[0, 5]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend />
                            <Area
                              type="monotone"
                              dataKey="average_rating"
                              stroke={CHART_COLORS.success}
                              fill={CHART_COLORS.gradient.primary}
                              strokeWidth={1}
                            />
                            <Line
                              type="monotone"
                              dataKey="average_rating"
                              name={t("average_rating")}
                              stroke={CHART_COLORS.success}
                              strokeWidth={3}
                              dot={{ fill: CHART_COLORS.success, strokeWidth: 2, r: 5 }}
                              activeDot={{ r: 7, stroke: CHART_COLORS.success, strokeWidth: 3, fill: "white" }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </ChartErrorBoundary>
                </div>

                {/* Study Time and Activity Patterns */}
                <div className="grid lg:grid-cols-2 gap-8">
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h4 className="text-lg font-semibold flex items-center gap-2">
                        <Clock className="h-5 w-5 text-primary" />
                        {t("totalTimeStudyingFlashcards")}
                      </h4>
                      <Badge variant="outline" className="text-xs">
                        {totalStudyTimeData.length} sessions
                      </Badge>
                    </div>

                    <ChartErrorBoundary>
                      <div className="h-80 p-4 bg-gradient-to-br from-muted/20 to-muted/5 rounded-xl border border-border/30">
                        {totalStudyTimeData.length === 0 ? (
                          <div className="flex items-center justify-center h-full">
                            <div className="text-center space-y-2">
                              <Clock className="h-12 w-12 text-muted-foreground mx-auto" />
                              <p className="text-muted-foreground">No study time data available</p>
                            </div>
                          </div>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={totalStudyTimeData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                              <defs>
                                <linearGradient id="colorStudyTime" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8} />
                                  <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.1} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                              <XAxis
                                dataKey="date"
                                stroke="hsl(var(--muted-foreground))"
                                fontSize={12}
                              />
                              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                              <Tooltip content={<CustomTooltip />} />
                              <Area
                                type="monotone"
                                dataKey="total_study_time"
                                name={t("total_study_time")}
                                stroke={CHART_COLORS.primary}
                                fill="hsl(var(--muted-foreground))"
                                strokeWidth={2}
                              />
                            </AreaChart>
                          </ResponsiveContainer>
                        )}
                      </div>
                    </ChartErrorBoundary>
                  </div>

                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h4 className="text-lg font-semibold flex items-center gap-2">
                        <Activity className="h-5 w-5 text-primary" />
                        {t("flashcardsSolvedByHour")}
                      </h4>
                      <Badge variant="outline" className="text-xs">
                        24h pattern
                      </Badge>
                    </div>

                    <ChartErrorBoundary>
                      <div className="h-80 p-4 bg-gradient-to-br from-muted/20 to-muted/5 rounded-xl border border-border/30">
                        {flashcardsByHourData.length === 0 ? (
                          <div className="flex items-center justify-center h-full">
                            <div className="text-center space-y-2">
                              <Activity className="h-12 w-12 text-muted-foreground mx-auto" />
                              <p className="text-muted-foreground">No hourly activity data available</p>
                            </div>
                          </div>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={flashcardsByHourData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                              <defs>
                                <linearGradient id="hourGradient" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor={CHART_COLORS.info} stopOpacity={0.8} />
                                  <stop offset="95%" stopColor={CHART_COLORS.info} stopOpacity={0.6} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                              <XAxis dataKey="hour" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                              <Tooltip content={<CustomTooltip />} />
                              <Bar dataKey="count" name={t("count")} fill="hsl(var(--muted-foreground))" radius={[6, 6, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        )}
                      </div>
                    </ChartErrorBoundary>
                  </div>
                </div>

                {/* Flashcard Rating Distribution */}
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-semibold flex items-center gap-2">
                      <Target className="h-5 w-5 text-primary" />
                      {t("flashcardDifficultyDistribution")}
                    </h4>
                    <Badge variant="outline" className="text-xs">
                      {flashcardRatingDistribution.length} categories
                    </Badge>
                  </div>

                  <div className="grid md:grid-cols-2 gap-8">
                    <ChartErrorBoundary>
                      <div className="h-80 p-4 bg-gradient-to-br from-muted/20 to-muted/5 rounded-xl border border-border/30">
                        {flashcardRatingDistribution.length === 0 ? (
                          <div className="flex items-center justify-center h-full">
                            <div className="text-center space-y-2">
                              <Target className="h-12 w-12 text-muted-foreground mx-auto" />
                              <p className="text-muted-foreground">No rating data available</p>
                            </div>
                          </div>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={flashcardRatingDistribution}
                                cx="50%"
                                cy="50%"
                                outerRadius={100}
                                dataKey="count"
                                nameKey="rating"
                                label={({ name, percentage }) => `${name}: ${percentage}%`}
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
                              <Legend />
                            </PieChart>
                          </ResponsiveContainer>
                        )}
                      </div>
                    </ChartErrorBoundary>

                    <div className="space-y-4">
                      <h5 className="font-medium text-foreground">Rating</h5>
                      <div className="space-y-3">
                        {flashcardRatingDistribution.length === 0 ? (
                          <div className="text-center py-8">
                            <p className="text-muted-foreground">No rating data to display</p>
                          </div>
                        ) : (
                          flashcardRatingDistribution.map((item, index) => (
                            <div
                              key={item.rating}
                              className="flex items-center justify-between p-4 bg-gradient-to-r from-muted/30 to-muted/10 rounded-lg border border-border/30 hover:border-border/50 transition-colors"
                            >
                              <div className="flex items-center gap-3">
                                <div
                                  className="w-4 h-4 rounded-full shadow-sm"
                                  style={{
                                    backgroundColor:
                                      [CHART_COLORS.error, CHART_COLORS.warning, CHART_COLORS.success][index] ||
                                      CHART_COLORS.primary,
                                  }}
                                />
                                <span className="font-medium text-foreground">{item.rating}</span>
                                <div className="flex items-center gap-1">
                                  {item.rating === "Hard" && <XCircle className="h-3 w-3 text-error" />}
                                  {item.rating === "Good" && <Minus className="h-3 w-3 text-warning" />}
                                  {item.rating === "Easy" && <CheckCircle className="h-3 w-3 text-success" />}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold text-lg text-foreground">{item.count}</div>
                                <div className="text-sm text-muted-foreground">{item.percentage}%</div>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </div>
      </Card>

      {/* Enhanced Cookbook Section */}
      <CookbookSection />
    </div>
  )
}

export default EnhancedDashboard
