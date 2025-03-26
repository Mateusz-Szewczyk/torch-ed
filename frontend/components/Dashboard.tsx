"use client"

import type React from "react"
import { useEffect, useState, useContext, useMemo } from "react"
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
} from "recharts"
import { ChevronDown, ChevronUp, BookOpen, TestTube, Calendar } from "lucide-react"
import { AuthContext } from "@/contexts/AuthContext"
import { useTranslation } from "react-i18next"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

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
      <Card className="bg-popover border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">{label}</CardTitle>
        </CardHeader>
        <CardContent className="py-1">
          {payload.map((item, index) => (
            <p key={index} className="text-sm" style={{ color: item.color }}>
              {item.name}: {item.value}
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
    <div className="flex flex-col items-center justify-center h-screen">
      <h2 className="text-2xl mb-4 text-foreground">{t("loadingData")}</h2>
      <div className="w-64 h-3 bg-secondary rounded-full overflow-hidden">
        <div className="h-full bg-primary transition-all duration-300 ease-in-out" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{progress}%</p>
    </div>
  )
}

interface DateInputProps {
  id: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  label: string
}

const DateInput: React.FC<DateInputProps> = ({ id, value, onChange, label }) => {
  return (
    <div className="relative">
      <label htmlFor={id} className="block text-sm font-medium text-foreground mb-1">
        {label}
      </label>
      <div className="relative">
        <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
        <input
          id={id}
          type="date"
          value={value}
          onChange={onChange}
          className="pl-10 pr-3 py-2 w-full border border-input rounded-md bg-background text-foreground focus:ring-2 focus:ring-ring focus:border-ring"
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
}) => {
  const { t } = useTranslation()
  return (
    <Card className="mb-8">
      <CardContent className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
              onValueChange={(value) => setSelectedExamId(value ? Number.parseInt(value) : null)}
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
              onValueChange={(value) => setSelectedDeckId(value ? Number.parseInt(value) : null)}
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
    <Card>
      <CardHeader>
        <CardTitle>{t("cookbookTitle")}</CardTitle>
        <CardDescription>{t("cookbookIntro")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 p-6">
        <div>
          <h3 className="text-lg font-semibold mb-2">{t("cookbook.flashcardsLimit")}</h3>
          <p>{t("cookbook.flashcardsLimitInfo")}</p>
        </div>
        <div>
          <h3 className="text-lg font-semibold mb-2">{t("cookbook.promptInstructions")}</h3>
          <p>{t("cookbook.promptIntro")}</p>
          <Card className="mt-2">
            <CardHeader>
              <CardTitle className="text-base">{t("cookbook.example1Title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm italic">
                &#34;Please generate 40 flashcards for studying before the computer networks exam, using the file I uploaded
                earlier.&#34;
              </p>
            </CardContent>
          </Card>
          <Card className="mt-2">
            <CardHeader>
              <CardTitle className="text-base">{t("cookbook.example2Title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm italic">
                &#34;Please create an exam for studying before the computer networks exam consisting of 30 questions, using
                the file I uploaded earlier.&#34;
              </p>
            </CardContent>
          </Card>
        </div>
        <p>{t("cookbook.usageTips")}</p>
        <div>
          <h3 className="text-lg font-semibold mb-2">{t("cookbook.chatUseExplanation")}</h3>
          <p>{t("cookbook.chatUseExplanationInfo")}</p>
        </div>
        <div>
          <h3 className="text-lg font-semibold mb-2">{t("cookbook.waitTimeExplanation")}</h3>
          <p>{t("cookbook.waitTimeExplanationInfo")}</p>
        </div>
        <div>
          <h3 className="text-lg font-semibold mb-2">{t("cookbook.progressTracking")}</h3>
          <p>{t("cookbook.progressTrackingInfo")}</p>
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

  // Filtry
  const [filterStartDate, setFilterStartDate] = useState<string>("")
  const [filterEndDate, setFilterEndDate] = useState<string>("")
  const [selectedExamId, setSelectedExamId] = useState<number | null>(null)
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null)

  // UI state for collapsible sections
  const [isExamAnalysisOpen, setIsExamAnalysisOpen] = useState<boolean>(false)
  const [isFlashcardAnalysisOpen, setIsFlashcardAnalysisOpen] = useState<boolean>(false)

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        setProgress(10)

        if (!isAuthenticated) {
          throw new Error(t("pleaseLogin"))
        }

        const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"
        const response = await fetch(`${API_BASE_URL}/dashboard/`, {
          credentials: "include",
        })

        setProgress(50)

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

  // Opcje talii
  const deckOptions = useMemo(() => {
    if (!data) return []
    return Object.entries(data.deck_names).map(([id, name]) => ({
      id: Number.parseInt(id, 10),
      name,
    }))
  }, [data])

  // Opcje egzaminów
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

  // Filtrowanie i obróbka danych
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
    return buckets
  }, [filteredData])

  const combinedExamData = useMemo(() => {
    if (!filteredData) return []
    const combinedMap = new Map<string, { study_sessions: number; exams_completed: number }>()
    filteredData.study_sessions.forEach((session) => {
      const date = session.started_at.split("T")[0]
      if (!combinedMap.has(date)) {
        combinedMap.set(date, { study_sessions: 0, exams_completed: 0 })
      }
      combinedMap.get(date)!.study_sessions += 1
    })
    filteredData.exam_results.forEach((exam) => {
      const date = exam.started_at.split("T")[0]
      if (!combinedMap.has(date)) {
        combinedMap.set(date, { study_sessions: 0, exams_completed: 0 })
      }
      combinedMap.get(date)!.exams_completed += 1
    })
    return sortByDateAscending(
      Array.from(combinedMap.entries()).map(([date, counts]) => ({
        date,
        study_sessions: counts.study_sessions,
        exams_completed: counts.exams_completed,
      })),
    )
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

  const nextReviewTimelineData = useMemo(() => {
    if (!filteredData) return []
    const reviewMap = new Map<string, number>()
    filteredData.user_flashcards
      .filter((card) => card.next_review)
      .forEach((card) => {
        const date = card.next_review.split("T")[0]
        reviewMap.set(date, (reviewMap.get(date) || 0) + 1)
      })
    return sortByDateAscending(Array.from(reviewMap.entries()).map(([date, count]) => ({ date, count })))
  }, [filteredData])

  const flashcardsSolvedDaily = useMemo(() => {
    if (!filteredData) return []
    const solvedMap = new Map<string, number>()
    filteredData.study_records
      .filter((record) => record.session_id !== null)
      .forEach((record) => {
        const date = record.reviewed_at.split("T")[0]
        solvedMap.set(date, (solvedMap.get(date) || 0) + 1)
      })
    return sortByDateAscending(Array.from(solvedMap.entries()).map(([date, count]) => ({ date, count })))
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
      .map(([hour, count]) => ({ hour, count }))
  }, [filteredData])

  const averageFlashcardsSolved = useMemo(() => {
    if (flashcardsSolvedDaily.length === 0) return 0
    const total = flashcardsSolvedDaily.reduce((acc, record) => acc + record.count, 0)
    return total / flashcardsSolvedDaily.length
  }, [flashcardsSolvedDaily])

  if (loading) {
    return <LoadingSpinner progress={progress} />
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">{t("error")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!filteredData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{t("noData")}</CardTitle>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 space-y-8">
      <h1 className="text-4xl font-bold text-center text-primary mb-8">{t("dashboardTitle")}</h1>

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
      />

      {/* Exam Analysis Section as a clickable header */}
      <Card>
        <button
          type="button"
          onClick={() => setIsExamAnalysisOpen(!isExamAnalysisOpen)}
          className="w-full p-2 text-left"
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 hover:bg-muted p-2 rounded transition-colors duration-200">
            <CardTitle className="text-2xl font-bold flex items-center">
              <TestTube className="mr-2 h-6 w-6" />
              {t("examAnalysis")}
            </CardTitle>
            {isExamAnalysisOpen ? <ChevronUp /> : <ChevronDown />}
          </CardHeader>
        </button>
        <CardContent className={"p-0"}>
          {isExamAnalysisOpen && (
            <div className="space-y-8 p-6">
              {filteredData.exam_results.length === 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle>{t("noExams.title")}</CardTitle>
                    <CardDescription>{t("noExams.description")}</CardDescription>
                  </CardHeader>
                  <CardFooter>
                    <Button asChild>
                      <Link href="/tests">{t("noExams.addExam")}</Link>
                    </Button>
                  </CardFooter>
                </Card>
              ) : (
                <>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("averageExamScoresOverTime")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={examLineChartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis domain={[0, 100]} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="average_score"
                          name={t("average_score")}
                          stroke="hsl(var(--primary))"
                          strokeWidth={2}
                          dot={{ fill: "hsl(var(--primary))" }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("timeSpentStudyingExams")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={examStudyTimeData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Bar dataKey="study_time" name={t("study_time")} fill="hsl(var(--primary))" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("examScoreDistribution")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={histogramExamResultsData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="score" />
                        <YAxis />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Bar dataKey="count" name={t("count")} fill="hsl(var(--primary))" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("sessionsAndExamsPerDay")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={combinedExamData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Bar dataKey="study_sessions" name={t("study_sessions")} fill="hsl(var(--primary))" />
                        <Bar dataKey="exams_completed" name={t("exams_completed")} fill="hsl(var(--secondary))" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Flashcard Analysis Section as a clickable header */}
      <Card>
        <button
          type="button"
          onClick={() => setIsFlashcardAnalysisOpen(!isFlashcardAnalysisOpen)}
          className="w-full text-left p-2"
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 hover:bg-muted p-2 rounded transition-colors duration-200">
            <CardTitle className="text-2xl font-bold flex items-center">
              <BookOpen className="mr-2 h-6 w-6" />
              {t("flashcardAnalysis")}
            </CardTitle>
            {isFlashcardAnalysisOpen ? <ChevronUp /> : <ChevronDown />}
          </CardHeader>
        </button>
        <CardContent className={"p-0"}>
          {isFlashcardAnalysisOpen && (
            <div className="space-y-8 p-6">
              {filteredData.user_flashcards.length === 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle>{t("noFlashcards.title")}</CardTitle>
                    <CardDescription>{t("noFlashcards.description")}</CardDescription>
                  </CardHeader>
                  <CardFooter>
                    <Button asChild>
                      <Link href="/flashcards">{t("noFlashcards.addFlashcards")}</Link>
                    </Button>
                  </CardFooter>
                </Card>
              ) : (
                <>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("averageFlashcardRatingsOverTime")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={flashcardLineChartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis domain={[0, 5]} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="average_rating"
                          name={t("average_rating")}
                          stroke="hsl(var(--primary))"
                          strokeWidth={2}
                          dot={{ fill: "hsl(var(--primary))" }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("totalTimeStudyingFlashcards")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <AreaChart data={totalStudyTimeData}>
                        <defs>
                          <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Area
                          type="monotone"
                          dataKey="total_study_time"
                          name={t("total_study_time")}
                          stroke="hsl(var(--primary))"
                          fill="url(#colorUv)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("flashcardsSolvedByHour")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={flashcardsByHourData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="hour" />
                        <YAxis />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Bar dataKey="count" name={t("count")} fill="hsl(var(--primary))" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("plannedStudySessions")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={nextReviewTimelineData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="count"
                          name={t("count")}
                          stroke="hsl(var(--primary))"
                          strokeWidth={2}
                          dot={{ fill: "hsl(var(--primary))" }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">{t("flashcardsSolvedDaily")}</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={flashcardsSolvedDaily}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Bar dataKey="count" name={t("count")} fill="hsl(var(--primary))" />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="mt-4">
                      {t("averageFlashcardsSolvedDaily")} <strong>{averageFlashcardsSolved.toFixed(2)}</strong>
                    </p>
                  </div>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <CookbookSection />
    </div>
  )
}

export default Dashboard
