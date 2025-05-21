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
    Math.min(sanitizedQuestions.length, 1)
  )
  const [isSelectionStep, setIsSelectionStep] = useState(true)
  const [selectedQuestions, setSelectedQuestions] =
    useState<ExamQuestion[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [score, setScore] = useState(0)
  const [userAnswers, setUserAnswers] = useState<UserAnswer[]>([])
  const [isExamCompleted, setIsExamCompleted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  // Dodajemy nową flagę, która zapamiętuje, czy wyniki zostały już wysłane
  const [resultSubmitted, setResultSubmitted] = useState(false)

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"

  // Filter answered questions
  const answeredQuestions = userAnswers.filter(
    (ans) => ans.selected_answer_id !== null && ans.selected_answer_id !== undefined
  )

  // Shuffle and pick random questions
  const selectRandomQuestions = (
    all: ExamQuestion[],
    count: number
  ): ExamQuestion[] => {
    const shuffled = [...all].sort(() => 0.5 - Math.random())
    return shuffled.slice(0, count)
  }

  // Slider change
  const handleSliderChange = (values: number[]) => {
    setNumQuestions(values[0])
  }

  // Input change
  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = parseInt(e.target.value, 10)
    if (!isNaN(value)) {
      const clamped = Math.min(
        Math.max(value, 1),
        sanitizedQuestions.length
      )
      setNumQuestions(clamped)
    }
  }

  // Start exam
  const startExam = () => {
    const questions = selectRandomQuestions(
      sanitizedQuestions,
      numQuestions
    )
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
    // Resetujemy flagę wysłania wyników przy każdym nowym egzaminie
    setResultSubmitted(false)
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
    if (currentQuestionIndex < selectedQuestions.length - 1) {
      setCurrentQuestionIndex((i) => i + 1)
    } else {
      setIsExamCompleted(true)
    }
  }

  // Restart exam
  const handleRestart = () => {
    setCurrentQuestionIndex(0)
    setScore(0)
    const initial = selectedQuestions.map((q) => ({
      question_id: q.id!,
      selected_answer_id: null,
      answer_time: null,
    }))

    setUserAnswers(initial)
    setIsExamCompleted(false)
    setIsSelectionStep(true)
    // Resetujemy flagę wysłania wyników
    setResultSubmitted(false)
  }

  // Submit result
  const submitExamResult = useCallback(async () => {
    // Dodajemy warunek, że jeśli wyniki już zostały wysłane, to nie wysyłamy ich ponownie
    if (resultSubmitted) return

    if (answeredQuestions.length === 0) {
      alert(t("no_answers_to_submit"))
      return
    }
    if (isSubmitting) return

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
      // Ustawiamy flagę, że wyniki zostały pomyślnie wysłane
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


  // Auto submit on complete - uruchamia się tylko, gdy egzamin jest ukończony i wyniki nie zostały jeszcze wysłane
  useEffect(() => {
    if (isExamCompleted && !resultSubmitted && !isSubmitting) {
      submitExamResult()
    }
  }, [isExamCompleted, submitExamResult, resultSubmitted, isSubmitting])

  const examCardMarginRight =
    !isMobileScreen && isChatOpen ? "mr-[40%]" : ""

  // Selection step
  if (isSelectionStep) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <div className="bg-card p-4 md:p-8 rounded-lg shadow-md w-full max-w-md">
          <div className="flex justify-end mb-4">
            <Button onClick={onExit} variant="ghost" size="sm">
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">{t("back")}</span>
            </Button>
          </div>
          <h2 className="text-xl md:text-2xl font-bold mb-4 text-primary text-center">
            {t("select_number_of_questions")}
          </h2>
          <div className="flex flex-col items-center">
            <div className="w-full mb-4">
              <Slider.Root
                className="relative flex items-center select-none touch-none w-full h-5"
                value={[numQuestions]}
                min={1}
                max={Math.min(sanitizedQuestions.length, 50)}
                step={1}
                onValueChange={handleSliderChange}
                aria-label="Number of questions"
              >
                <Slider.Track className="bg-muted relative grow rounded-full h-1">
                  <Slider.Range className="bg-primary absolute rounded-full h-full" />
                </Slider.Track>
                <Slider.Thumb className="block w-3 h-3 bg-primary rounded-full shadow focus:outline-none focus:ring" />
              </Slider.Root>
            </div>
            <div className="flex items-center space-x-1 mb-6">
              <span className="text-xs text-muted-foreground">{t("number_of_questions")}:</span>
              <input
                type="number"
                min={1}
                max={Math.min(sanitizedQuestions.length, 50)}
                value={numQuestions}
                onChange={handleInputChange}
                className="w-12 p-1 border border-input rounded-md bg-background text-xs"
              />
            </div>
            <Button onClick={startExam} variant="default" size="sm" className="w-full">
              <ChevronRight className="h-4 w-4" />
              <span className="text-xs">{t("start_exam")}</span>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Summary step
  if (isExamCompleted) {
    return (
      <div className="p-4 md:p-8 flex flex-col items-center justify-center min-h-screen bg-background">
        <div className="bg-card p-4 md:p-8 rounded-lg shadow-md w-full max-w-2xl text-center">
          <h2 className="text-xl md:text-3xl font-bold mb-4 text-primary">
            {t("exam_summary")}
          </h2>
          <p className="text-sm md:text-xl mb-6 text-secondary">
            {t("you_scored")} {score} {t("out_of")} {selectedQuestions.length}
          </p>
          {isSubmitting && (
            <div className="flex items-center justify-center space-x-1 mb-4">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-xs">{t("submitting_results")}</span>
            </div>
          )}
          {submitError && (
            <p className="text-xs md:text-sm text-destructive mb-4">
              {t("error_submitting_results")} {submitError}
            </p>
          )}
          <div className="flex justify-center space-x-2">
            <Button onClick={handleRestart} variant="default" size="sm">
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">{t("restart_exam")}</span>
            </Button>
            <Button onClick={onExit} variant="destructive" size="sm">
              <XCircle className="h-4 w-4" />
              <span className="text-xs">{t("exit_study")}</span>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // In-progress step
  const currentQuestion = selectedQuestions[currentQuestionIndex]

  return (
    <div className="h-screen w-full bg-background flex flex-col md:flex-row items-center justify-center p-4">
      <div className={`${examCardMarginRight} w-full md:w-2/3 max-w-2xl p-2 md:p-4`}>
        <div className="bg-card p-4 md:p-6 rounded-lg shadow-md w-full">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg md:text-2xl font-bold text-primary">
              {exam.name}
            </h2>
            <Button variant="secondary" onClick={() => setIsChatOpen(!isChatOpen)} size="sm">
              <MessageCircle className="h-4 w-4" />
              <span className="text-xs">
                {isChatOpen ? t("hide_chat") : t("show_chat")}
              </span>
            </Button>
          </div>
          <p className="mb-4 text-xs md:text-sm">{exam.description}</p>
          <div className="mb-4">
            <h3 className="text-sm md:text-lg font-semibold mb-2">
              {t("question")}:{currentQuestion.text}
            </h3>
            <div className="grid grid-cols-1 gap-2">
              {currentQuestion.answers.map((answer) => {
                const isSelected = userAnswers[currentQuestionIndex]?.selected_answer_id === answer.id
                const isCorrect = answer.is_correct
                return (
                  <Button
                    key={`answer-${answer.id}`}
                    variant={isSelected ? (isCorrect ? "default" : "destructive") : "outline"}
                    onClick={() => handleAnswerSelect(answer.id)}
                    disabled={userAnswers[currentQuestionIndex]?.selected_answer_id !== null && userAnswers[currentQuestionIndex]?.selected_answer_id !== undefined}
                    size="sm"
                  >
                    {isSelected && isCorrect && <CheckCircle className="h-4 w-4 text-success" />}
                    {isSelected && !isCorrect && <XCircle className="h-4 w-4 text-destructive" />}
                    <span className="text-xs">{answer.text}</span>
                  </Button>
                )
              })}
            </div>
          </div>
          <div className="flex justify-between mt-4">
            <Button
              onClick={() => setCurrentQuestionIndex((i) => Math.max(i - 1, 0))}
              disabled={currentQuestionIndex === 0}
              variant="ghost"
              size="sm"
            >
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">{t("previous")}</span>
            </Button>
            <Button
              variant="default"
              onClick={() => {
                if (userAnswers[currentQuestionIndex]?.selected_answer_id !== null && userAnswers[currentQuestionIndex]?.selected_answer_id !== undefined) {
                  if (currentQuestionIndex < selectedQuestions.length - 1) {
                    setCurrentQuestionIndex((i) => i + 1)
                  } else {
                    setIsExamCompleted(true)
                  }
                }
              }}
              disabled={userAnswers[currentQuestionIndex]?.selected_answer_id === null || userAnswers[currentQuestionIndex]?.selected_answer_id === undefined}
              size="sm"
            >
              <span className="text-xs">
                {currentQuestionIndex < selectedQuestions.length - 1 ? t("next") : t("finish")}
              </span>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          {isSubmitting && (
            <div className="flex items-center space-x-1 mt-4">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-xs">{t("submitting_results")}</span>
            </div>
          )}
          {submitError && (
            <p className="text-xs md:text-sm text-destructive mt-4">
              {t("error_submitting_results")} {submitError}
            </p>
          )}
          <div className="flex justify-center space-x-2 mt-4">
            <Button onClick={handleRestart} variant="default" size="sm">
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">{t("restart_exam")}</span>
            </Button>
            <Button
              variant="secondary"
              onClick={submitExamResult}
              // Nie pozwalamy na ponowne wysłanie, jeśli wyniki zostały już wysłane
              disabled={isSubmitting || answeredQuestions.length === 0 || resultSubmitted}
              size="sm"
            >
              <span className="text-xs">
                {resultSubmitted ? t("results_saved") || "Results Saved" : t("save_attempt")}
              </span>
            </Button>
            <Button variant="destructive" onClick={onExit} size="sm">
              <XCircle className="h-4 w-4" />
              <span className="text-xs">{t("exit_study")}</span>
            </Button>
          </div>
        </div>
      </div>
      {isChatOpen && (
        <div className="fixed top-0 left-0 w-full h-full md:w-[40%] md:right-0 md:left-auto bg-background md:border-l border-border z-50">
          <div className="absolute top-4 left-4 md:hidden">
            <Button variant="ghost" size="sm" onClick={() => setIsChatOpen(false)}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </div>
          <Chat conversationId={exam.conversation_id || 0} />
        </div>
      )}
      {!isMobileScreen && isChatOpen && (
        <div className="w-[40%] h-full fixed right-0 top-0 bg-background border-l border-border z-50">
          <Chat conversationId={exam.conversation_id || 0} />
        </div>
      )}
    </div>
  )
}