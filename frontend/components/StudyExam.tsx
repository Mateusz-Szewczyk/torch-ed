"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { useTranslation } from "react-i18next"
import {
  ChevronRight,
  ChevronLeft,
  CheckCircle,
  XCircle,
  MessageCircle,
  ArrowLeft,
  Loader2,
  Clock,
  Target,
  Award,
  RotateCcw,
  Save,
  X,
} from "lucide-react"
import * as Slider from "@radix-ui/react-slider"
import Chat from "@/components/Chat"
import type { Exam, ExamQuestion } from "@/types"

interface StudyExamProps {
  exam: Exam
  onExit: () => void
}

interface ExamResultAnswerCreate {
  question_id: number | undefined
  selected_answer_id: number | undefined
  answer_time: string | undefined
}

interface ExamResultCreate {
  exam_id: number
  answers: ExamResultAnswerCreate[]
}

interface ExamResultRead {
  id: number
  exam_id: number
  user_id: string
  started_at: string
  completed_at: string | null
  score: number | null
  answers: undefined[]
}

interface UserAnswer {
  question_id: number | undefined
  selected_answer_id: number | undefined | null
  answer_time: string | undefined | null
}

export function StudyExam({ exam, onExit }: StudyExamProps) {
  const { t } = useTranslation()

  // Chat and viewport
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isMobileScreen, setIsMobileScreen] = useState(false)

  useEffect(() => {
    const handleResize = () => setIsMobileScreen(window.innerWidth < 768)
    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  // Sanitize exam questions (ensure numeric IDs)
  const sanitizedQuestions = useMemo<ExamQuestion[]>(() => {
    return exam.questions.map((q) => ({
      ...q,
      id: Number(q.id),
      answers: q.answers.map((a) => ({ ...a, id: Number(a.id) })),
    }))
  }, [exam.questions])

  // Exam state
  const [numQuestions, setNumQuestions] = useState<number>(
    Math.min(sanitizedQuestions.length, 10)
  )
  const [isSelectionStep, setIsSelectionStep] = useState(true)
  const [selectedQuestions, setSelectedQuestions] = useState<ExamQuestion[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [score, setScore] = useState(0)
  const [userAnswers, setUserAnswers] = useState<UserAnswer[]>([])
  const [isExamCompleted, setIsExamCompleted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [resultSubmitted, setResultSubmitted] = useState(false)
  const [startTime, setStartTime] = useState<Date | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"

  // Filter answered questions
  const answeredQuestions = userAnswers.filter(
    (ans) => ans.selected_answer_id !== null && ans.selected_answer_id !== undefined
  )

  // Calculate completion percentage
  const completionPercentage = selectedQuestions.length > 0
    ? Math.round((answeredQuestions.length / selectedQuestions.length) * 100)
    : 0

  // Calculate elapsed time
  const getElapsedTime = () => {
    if (!startTime) return "00:00"
    const now = new Date()
    const diff = Math.floor((now.getTime() - startTime.getTime()) / 1000)
    const minutes = Math.floor(diff / 60)
    const seconds = diff % 60
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }

  // Shuffle and pick random questions
  const selectRandomQuestions = (all: ExamQuestion[], count: number): ExamQuestion[] => {
    const shuffled = [...all].sort(() => 0.5 - Math.random())
    return shuffled.slice(0, count)
  }

  // Slider change
  const handleSliderChange = (values: number[]) => {
    setNumQuestions(values[0])
  }

  // Input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10)
    if (!isNaN(value)) {
      const clamped = Math.min(Math.max(value, 1), sanitizedQuestions.length)
      setNumQuestions(clamped)
    }
  }

  // Start exam
  const startExam = () => {
    const questions = selectRandomQuestions(sanitizedQuestions, numQuestions)
    setSelectedQuestions(questions)
    const initialAnswers = questions.map((q) => ({
      question_id: q.id!,
      selected_answer_id: null,
      answer_time: null,
    }))
    setUserAnswers(initialAnswers)
    setScore(0)
    setCurrentQuestionIndex(0)
    setIsSelectionStep(false)
    setResultSubmitted(false)
    setStartTime(new Date())
    setSubmitError(null)
  }

  // Answer select
  const handleAnswerSelect = (answerId: number | undefined) => {
    const current = selectedQuestions[currentQuestionIndex]
    const answerTime = new Date().toISOString()
    const updated = [...userAnswers]
    updated[currentQuestionIndex] = {
      question_id: current.id,
      selected_answer_id: answerId,
      answer_time: answerTime,
    }
    setUserAnswers(updated)
    const selected = current.answers.find((a) => a.id === answerId)
    if (selected?.is_correct) setScore((s) => s + 1)
  }

  // Navigate to previous question
  const goToPreviousQuestion = () => {
    setCurrentQuestionIndex((i) => Math.max(i - 1, 0))
  }

  // Restart exam
  const handleRestart = () => {
    setCurrentQuestionIndex(0)
    setScore(0)
    setIsExamCompleted(false)
    setIsSelectionStep(true)
    setResultSubmitted(false)
    setStartTime(null)
    setSubmitError(null)
    setUserAnswers([])
    setSelectedQuestions([])
  }

  // Submit result
  const submitExamResult = useCallback(async () => {
    if (resultSubmitted || isSubmitting) return
    if (answeredQuestions.length === 0) {
      alert(t("no_answers_to_submit"))
      return
    }

    const payload: ExamResultCreate = {
      exam_id: exam.id,
      answers: answeredQuestions.map((a) => ({
        question_id: a.question_id,
        selected_answer_id: a.selected_answer_id!,
        answer_time: a.answer_time!,
      })),
    }

    try {
      setIsSubmitting(true)
      setSubmitError(null)
      const res = await fetch(`${API_BASE_URL}/exams/submit/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || "Error submitting exam result.")
      }
      const result = (await res.json()) as ExamResultRead
      console.log("Exam result saved:", result)
      setResultSubmitted(true)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setSubmitError(err.message)
      } else {
        setSubmitError("Unknown error submitting exam result.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }, [answeredQuestions, API_BASE_URL, exam.id, t, isSubmitting, resultSubmitted])

  // Auto submit on complete
  useEffect(() => {
    if (isExamCompleted && !resultSubmitted && !isSubmitting && answeredQuestions.length > 0) {
      submitExamResult()
    }
  }, [isExamCompleted, submitExamResult, resultSubmitted, isSubmitting, answeredQuestions.length])

  const examCardMarginRight = !isMobileScreen && isChatOpen ? "mr-[40%]" : ""

  // Selection step
  if (isSelectionStep) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <div className="bg-card p-6 md:p-8 rounded-lg shadow-md w-full max-w-md space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl md:text-2xl font-bold text-primary">
              {t("select_number_of_questions")}
            </h2>
            <Button
              onClick={onExit}
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-primary"
              aria-label={t("back")}
            >
              <X className="h-4 w-4" />
              <span className="sr-only">{t("back")}</span>
            </Button>
          </div>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground block mb-2">
                  {t("number_of_questions")}
                </label>
                <Slider.Root
                  className="relative flex items-center select-none touch-none w-full h-6"
                  value={[numQuestions]}
                  min={1}
                  max={Math.min(sanitizedQuestions.length, 50)}
                  step={1}
                  onValueChange={handleSliderChange}
                  aria-label={t("number_of_questions")}
                  aria-valuetext={`${numQuestions} questions`}
                >
                  <Slider.Track className="bg-muted relative grow rounded-full h-1">
                    <Slider.Range className="bg-primary absolute rounded-full h-full transition-all duration-300" />
                  </Slider.Track>
                  <Slider.Thumb className="block w-5 h-5 bg-primary rounded-full shadow focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all duration-200 hover:scale-110">
                    <span className="absolute -top-6 text-xs text-muted-foreground bg-background px-1 rounded">
                      {numQuestions}
                    </span>
                  </Slider.Thumb>
                </Slider.Root>
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-2 sr-only">
                  {t("number_of_questions")}
                </label>
                <input
                  type="number"
                  min={1}
                  max={Math.min(sanitizedQuestions.length, 50)}
                  value={numQuestions}
                  onChange={handleInputChange}
                  className="w-16 p-1 border border-input rounded-md bg-background text-sm text-center"
                  aria-label={t("number_of_questions")}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">
                  {numQuestions}
                </div>
                <div className="text-sm text-muted-foreground">
                  {t("questions")}
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">
                  ~{Math.ceil(numQuestions * 0.7)}m
                </div>
                <div className="text-sm text-muted-foreground">
                  {t("estimated_time")}
                </div>
              </div>
            </div>
            <Button
              onClick={startExam}
              variant="default"
              size="lg"
              className="w-full hover:scale-105 transition-transform duration-200"
            >
              <Target className="h-5 w-5 mr-2" />
              <span className="text-sm">{t("start_exam")}</span>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Summary step
  if (isExamCompleted) {
    const scorePercentage = Math.round((score / selectedQuestions.length) * 100)
    const isPassing = scorePercentage >= 70

    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <div className="bg-card p-6 md:p-8 rounded-lg shadow-md w-full max-w-2xl space-y-6">
          <div className="text-center">
            <div className={`inline-flex items-center justify-center w-20 h-20 rounded-full mb-6 bg-muted`}>
              <Award className={`w-10 h-10 ${isPassing ? 'text-primary' : 'text-destructive'}`} />
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-primary mb-2">
              {t("exam_complete")}
            </h2>
            <p className="text-muted-foreground">
              {isPassing ? t("congratulations_passed") : t("keep_practicing")}
            </p>
          </div>
          <div className="space-y-6">
            <div className="text-center p-6 bg-muted rounded-lg">
              <div className="text-4xl font-bold text-primary mb-2">
                {score}/{selectedQuestions.length}
              </div>
              <div className="text-lg text-muted-foreground">
                {scorePercentage}% {t("correct")}
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-muted rounded-lg">
                <CheckCircle className="w-8 h-8 text-primary mx-auto mb-2" />
                <div className="text-2xl font-bold text-primary">
                  {score}
                </div>
                <div className="text-sm text-muted-foreground">
                  {t("correct_answers")}
                </div>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <XCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
                <div className="text-2xl font-bold text-primary">
                  {selectedQuestions.length - score}
                </div>
                <div className="text-sm text-muted-foreground">
                  {t("incorrect_answers")}
                </div>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <Clock className="w-8 h-8 text-primary mx-auto mb-2" />
                <div className="text-2xl font-bold text-primary">
                  {getElapsedTime()}
                </div>
                <div className="text-sm text-muted-foreground">
                  {t("time_taken")}
                </div>
              </div>
            </div>
            {isSubmitting && (
              <div className="flex items-center justify-center space-x-2 p-4 bg-muted rounded-lg">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">{t("submitting_results")}</span>
              </div>
            )}
            {resultSubmitted && (
              <div className="flex items-center justify-center space-x-2 p-4 bg-muted rounded-lg">
                <CheckCircle className="w-5 h-5 text-primary" />
                <span className="text-sm text-muted-foreground">{t("results_saved_successfully")}</span>
              </div>
            )}
            {submitError && (
              <div className="p-4 bg-muted rounded-lg">
                <div className="flex items-center space-x-2">
                  <XCircle className="w-5 h-5 text-destructive" />
                  <div>
                    <div className="text-sm text-destructive">{t("error_submitting_results")}</div>
                    <div className="text-sm text-destructive">{submitError}</div>
                  </div>
                </div>
              </div>
            )}
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                onClick={handleRestart}
                variant="default"
                size="lg"
                className="flex-1 hover:scale-105 transition-transform duration-200"
              >
                <RotateCcw className="w-5 h-5 mr-2" />
                {t("try_again")}
              </Button>
              {!resultSubmitted && !isSubmitting && (
                <Button
                  onClick={submitExamResult}
                  variant="secondary"
                  size="lg"
                  className="flex-1 hover:scale-105 transition-transform duration-200"
                  disabled={answeredQuestions.length === 0}
                >
                  <Save className="w-5 h-5 mr-2" />
                  {t("save_results")}
                </Button>
              )}
              <Button
                onClick={onExit}
                variant="destructive"
                size="lg"
                className="flex-1 hover:scale-105 transition-transform duration-200"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                {t("back_to_exams")}
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // In-progress step
  const currentQuestion = selectedQuestions[currentQuestionIndex]
  const progressPercent = selectedQuestions.length > 0 ? ((currentQuestionIndex + 1) / selectedQuestions.length) * 100 : 0
  const currentAnswer = userAnswers[currentQuestionIndex]
  const hasAnswered = currentAnswer?.selected_answer_id !== null && currentAnswer?.selected_answer_id !== undefined

  return (
    <div className="h-screen w-full bg-background flex flex-col md:flex-row items-center justify-center p-4">
      <div className={`${examCardMarginRight} w-full md:w-2/3 max-w-2xl p-2 md:p-4`}>
        <div className="bg-card p-4 md:p-6 rounded-lg shadow-md space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg md:text-2xl font-bold text-primary">{exam.name}</h2>
              <p className="text-sm text-muted-foreground">{exam.description}</p>
            </div>
            <Button
              variant="secondary"
              onClick={() => setIsChatOpen(!isChatOpen)}
              size="sm"
              className="hover:scale-105 transition-transform duration-200"
              aria-label={isChatOpen ? t("hide_chat") : t("show_chat")}
            >
              <MessageCircle className="h-4 w-4 mr-1" />
              <span className="text-sm">{isChatOpen ? t("hide_chat") : t("show_chat")}</span>
            </Button>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>{t("question")} {currentQuestionIndex + 1} {t("of")} {selectedQuestions.length}</span>
              <span>{getElapsedTime()} ({completionPercentage}% {t("complete")})</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-primary">
              {t("question")}: {currentQuestion.text}
            </h3>
            <div className="grid grid-cols-1 gap-2">
              {currentQuestion.answers.map((answer, index) => {
                const isSelected = currentAnswer?.selected_answer_id === answer.id
                const showCorrect = hasAnswered && answer.is_correct
                const showIncorrect = hasAnswered && isSelected && !answer.is_correct
                return (
                  <Button
                    key={`answer-${answer.id}`}
                    variant={showCorrect ? "default" : showIncorrect ? "destructive" : isSelected ? "secondary" : "outline"}
                    onClick={() => !hasAnswered && handleAnswerSelect(answer.id)}
                    disabled={hasAnswered}
                    size="sm"
                    className="w-full flex items-center justify-start gap-2 text-sm hover:scale-105 transition-transform duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label={answer.text}
                    aria-disabled={hasAnswered}
                  >
                    <div className="w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-medium text-muted-foreground">
                      {showCorrect ? (
                        <>
                          <CheckCircle className="w-5 h-5 text-success" />
                          <span className="sr-only">{t("correct_answer")}</span>
                        </>
                      ) : showIncorrect ? (
                        <>
                          <XCircle className="w-5 h-5 text-destructive" />
                          <span className="sr-only">{t("incorrect_answer")}</span>
                        </>
                      ) : (
                        String.fromCharCode(65 + index)
                      )}
                    </div>
                    <span>{answer.text}</span>
                  </Button>
                )
              })}
            </div>
          </div>
          <div className="flex flex-col sm:flex-row justify-between gap-6">
            <div className="flex gap-2">
              <Button
                onClick={goToPreviousQuestion}
                disabled={currentQuestionIndex === 0}
                variant="ghost"
                size="sm"
                className="hover:scale-105 transition-transform duration-200"
                aria-label={t("previous")}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                <span className="text-sm">{t("previous")}</span>
              </Button>
              <Button
                variant="default"
                onClick={() => {
                  if (hasAnswered) {
                    if (currentQuestionIndex < selectedQuestions.length - 1) {
                      setCurrentQuestionIndex((i) => i + 1)
                    } else {
                      setIsExamCompleted(true)
                    }
                  }
                }}
                disabled={!hasAnswered}
                size="sm"
                className="hover:scale-105 transition-transform duration-200"
                aria-label={currentQuestionIndex < selectedQuestions.length - 1 ? t("next") : t("finish")}
              >
                <span className="text-sm">
                  {currentQuestionIndex < selectedQuestions.length - 1 ? t("next") : t("finish")}
                </span>
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
            <div className="flex gap-2 justify-center">
              <Button
                onClick={handleRestart}
                variant="default"
                size="sm"
                className="hover:scale-105 transition-transform duration-200 min-w-[45%]"
                aria-label={t("restart_exam")}
              >
                <RotateCcw className="h-4 w-4 mr-1" />
                <span className="text-sm">{t("restart_exam")}</span>
              </Button>
              <Button
                variant="secondary"
                onClick={submitExamResult}
                disabled={isSubmitting || answeredQuestions.length === 0 || resultSubmitted}
                size="sm"
                className="hover:scale-105 transition-transform duration-200 min-w-[45%]"
                aria-label={resultSubmitted ? t("results_saved") : t("save_attempt")}
              >
                <Save className="h-4 w-4 mr-1" />
                <span className="text-sm">
                  {resultSubmitted ? t("results_saved") : t("save_attempt")}
                </span>
              </Button>
            </div>
          </div>
            <Button
                  variant="destructive"
                  onClick={onExit}
                  size="sm"
                  className="hover:scale-105 transition-transform duration-200 w-full"
                  aria-label={t("exit_study")}
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  <span className="text-sm">{t("exit_study")}</span>
            </Button>
          {isSubmitting && (
            <div className="flex items-center space-x-2 mt-4">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">{t("submitting_results")}</span>
            </div>
          )}
          {submitError && (
            <p className="text-sm text-destructive mt-4">
              {t("error_submitting_results")} {submitError}
            </p>
          )}
        </div>
      </div>
      {isChatOpen && (
        <div className="fixed top-0 left-0 w-full h-full md:w-[40%] md:right-0 md:left-auto bg-background md:border-l border-border z-50 transition-all duration-300">
          <div className="absolute top-4 left-4 md:hidden z-40">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsChatOpen(false)}
              aria-label={t("close_chat")}
              className={"hover:scale-105 transition-transform duration-200 z-40"}
            >
              <ArrowLeft className="h-5 w-5 z-40" />
              <span className="sr-only">{t("close_chat")}</span>
            </Button>
          </div>
          <Chat conversationId={exam.conversation_id || 0} />
        </div>
      )}
      {!isMobileScreen && isChatOpen && (
        <div className="w-[40%] h-full fixed right-0 top-0 bg-background border-l border-border z-50 transition-all duration-300">
          <Chat conversationId={exam.conversation_id || 0} />
        </div>
      )}
    </div>
  )
}