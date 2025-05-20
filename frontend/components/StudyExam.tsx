"use client"

import type React from "react"
import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { useTranslation } from "react-i18next"
import { ChevronRight, ChevronLeft, CheckCircle, XCircle, MessageCircle, ArrowLeft, Loader2 } from "lucide-react"
import * as Slider from "@radix-ui/react-slider"
import Chat from "@/components/Chat"
import type { Exam, ExamQuestion } from "@/types"

interface StudyExamProps {
  exam: Exam
  onExit: () => void
}

interface ExamResultAnswerCreate {
  question_id: number
  selected_answer_id: number
  answer_time: string // ISO string
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
  answers: ExamResultAnswerRead[]
}

interface ExamResultAnswerRead {
  id: number
  question_id: number
  selected_answer_id: number
  is_correct: boolean
  answer_time: string
}

interface UserAnswer {
  question_id: number
  selected_answer_id: number | null
  answer_time: string | null
}

export function StudyExam({ exam, onExit }: StudyExamProps) {
  const { t } = useTranslation()

  // Stan chatu oraz detekcja rozmiaru ekranu
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false)
  const [isMobileScreen, setIsMobileScreen] = useState<boolean>(false)
  useEffect(() => {
    const handleResize = () => {
      setIsMobileScreen(window.innerWidth < 768)
    }
    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  // Stany dotyczące egzaminu
  const [numQuestions, setNumQuestions] = useState<number>(10)
  const [isSelectionStep, setIsSelectionStep] = useState<boolean>(true)
  const [selectedQuestions, setSelectedQuestions] = useState<ExamQuestion[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0)
  const [score, setScore] = useState<number>(0)
  const [userAnswers, setUserAnswers] = useState<UserAnswer[]>([])
  const [isExamCompleted, setIsExamCompleted] = useState<boolean>(false)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"

  // Odfiltrowanie odpowiedzi, które nie są puste
  const answeredQuestions = userAnswers.filter((answer) => answer.selected_answer_id !== null)

  // Funkcja losująca pytania z całej puli
  const selectRandomQuestions = (allQuestions: ExamQuestion[], count: number): ExamQuestion[] => {
    const shuffled = [...allQuestions].sort(() => 0.5 - Math.random())
    return shuffled.slice(0, count)
  }

  // Obsługa zmiany wartości suwaka
  const handleSliderChange = (values: number[]) => {
    setNumQuestions(values[0])
  }

  // Obsługa zmiany w inpucie
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number.parseInt(e.target.value, 10)
    if (!isNaN(value)) {
      const clampedValue = Math.min(Math.max(value, 1), exam.questions.length)
      setNumQuestions(clampedValue)
    }
  }

  // Rozpoczęcie egzaminu: wybór losowych pytań i inicjalizacja odpowiedzi
  const startExam = () => {
    const questions = selectRandomQuestions(exam.questions, numQuestions)
    setSelectedQuestions(questions)

    // Upewnij się, że question_id jest zawsze liczbą
    const initialUserAnswers: UserAnswer[] = questions.map((q) => ({
      question_id: q.id || 0, // Użyj 0 jako wartości domyślnej, jeśli id jest undefined
      selected_answer_id: null,
      answer_time: null,
    }))

    setUserAnswers(initialUserAnswers)
    setIsSelectionStep(false)
  }

  // Obsługa wyboru odpowiedzi
  const handleAnswerSelect = (answerId: number) => {
    const currentQuestion = selectedQuestions[currentQuestionIndex]
    const selectedAnswer = currentQuestion.answers.find((a) => a.id === answerId)
    const answerTime = new Date().toISOString()
    const updatedUserAnswers = [...userAnswers]
    updatedUserAnswers[currentQuestionIndex] = {
      question_id: currentQuestion.id || 0, // Użyj 0 jako wartości domyślnej, jeśli id jest undefined
      selected_answer_id: answerId,
      answer_time: answerTime,
    }
    setUserAnswers(updatedUserAnswers)
    if (selectedAnswer && selectedAnswer.is_correct) {
      setScore((prev) => prev + 1)
    }
    if (currentQuestionIndex < selectedQuestions.length - 1) {
      setCurrentQuestionIndex((prev) => prev + 1)
    } else {
      setIsExamCompleted(true)
    }
  }

  // Restart egzaminu
  const handleRestart = () => {
    setCurrentQuestionIndex(0)
    setScore(0)

    // Upewnij się, że question_id jest zawsze liczbą
    const initialUserAnswers: UserAnswer[] = selectedQuestions.map((q) => ({
      question_id: q.id || 0, // Użyj 0 jako wartości domyślnej, jeśli id jest undefined
      selected_answer_id: null,
      answer_time: null,
    }))

    setUserAnswers(initialUserAnswers)
    setIsExamCompleted(false)
    setIsSelectionStep(true)
  }

  // Wysyłanie wyniku egzaminu
  const submitExamResult = useCallback(async () => {
    if (answeredQuestions.length === 0) {
      alert(t("no_answers_to_submit"))
      return
    }
    const examResult: ExamResultCreate = {
      exam_id: exam.id,
      answers: answeredQuestions.map((answer) => ({
        question_id: answer.question_id,
        selected_answer_id: answer.selected_answer_id as number,
        answer_time: answer.answer_time as string,
      })),
    }
    try {
      setIsSubmitting(true)
      setSubmitError(null)
      const response = await fetch(`${API_BASE_URL}/exams/submit/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(examResult),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Error submitting exam result.")
      }
      const result: ExamResultRead = await response.json()
      console.log("Exam result saved:", result)
    } catch (error: unknown) {
      if (error instanceof Error) {
        console.error("Error submitting exam result:", error.message)
        setSubmitError(error.message)
      } else {
        console.error("Unknown error submitting exam result")
        setSubmitError("Unknown error submitting exam result.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }, [answeredQuestions, API_BASE_URL, exam.id, t])

  // Automatyczne wysłanie wyniku po ukończeniu egzaminu
  useEffect(() => {
    if (isExamCompleted) {
      submitExamResult()
    }
  }, [isExamCompleted, submitExamResult])

  // Dla widoku desktopowego – przesunięcie karty egzaminu, gdy chat jest otwarty
  const examCardMarginRight = !isMobileScreen && isChatOpen ? "mr-[40%]" : ""

  // Renderowanie kroku wyboru liczby pytań
  if (isSelectionStep) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <div className="bg-card p-4 md:p-8 rounded-lg shadow-md w-full max-w-md">
          <div className="flex justify-end mb-4">
            <Button onClick={onExit} variant="ghost" size="sm" className="flex items-center space-x-1">
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
                max={Math.min(exam.questions.length, 50)}
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
                max={Math.min(exam.questions.length, 50)}
                value={numQuestions}
                onChange={handleInputChange}
                className="w-12 p-1 border border-input rounded-md bg-background text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <Button
              onClick={startExam}
              variant="default"
              size="sm"
              className="w-full flex items-center justify-center space-x-1"
            >
              <ChevronRight className="h-4 w-4" />
              <span className="text-xs">{t("start_exam")}</span>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Renderowanie podsumowania egzaminu po jego ukończeniu
  if (isExamCompleted) {
    return (
      <div className="p-4 md:p-8 flex flex-col items-center justify-center min-h-screen bg-background">
        <div className="bg-card p-4 md:p-8 rounded-lg shadow-md w-full max-w-2xl text-center">
          <h2 className="text-xl md:text-3xl font-bold mb-4 text-primary">{t("exam_summary")}</h2>
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
              {t("error_submitting_results")}: {submitError}
            </p>
          )}
          <div className="flex justify-center space-x-2">
            <Button onClick={handleRestart} variant="default" size="sm" className="flex items-center space-x-1">
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">{t("restart_exam")}</span>
            </Button>
            <Button variant="destructive" onClick={onExit} size="sm" className="flex items-center space-x-1">
              <XCircle className="h-4 w-4" />
              <span className="text-xs">{t("exit_study")}</span>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Renderowanie egzaminu w trakcie
  const currentQuestion = selectedQuestions[currentQuestionIndex]

  return (
    <div className="h-screen w-full bg-background flex flex-col md:flex-row items-center justify-center p-4">
      <div className={`transition-all duration-300 ${examCardMarginRight} w-full md:w-2/3 max-w-2xl p-2 md:p-4`}>
        <div className="bg-card p-4 md:p-6 rounded-lg shadow-md w-full">
          <div className="flex flex-col md:flex-row justify-between items-center mb-4">
            <h2 className="text-lg md:text-2xl font-bold text-primary">{exam.name}</h2>
            <Button
              variant="secondary"
              onClick={() => setIsChatOpen(!isChatOpen)}
              size="sm"
              className="flex items-center space-x-1 mt-2 md:mt-0"
            >
              <MessageCircle className="h-4 w-4" />
              <span className="text-xs">{isChatOpen ? t("hide_chat") : t("show_chat")}</span>
            </Button>
          </div>
          <p className="mb-4 text-xs md:text-sm">{exam.description}</p>
          <div className="mb-4">
            <h3 className="text-sm md:text-lg font-semibold mb-2">
              {t("question")}: {currentQuestion.text}
            </h3>
            <div className="grid grid-cols-1 gap-2">
              {currentQuestion.answers.map((answer) => {
                const isSelected = userAnswers[currentQuestionIndex]?.selected_answer_id === answer.id
                const isCorrect = answer.is_correct
                return (
                  <Button
                    key={answer.id || 0} // Użyj 0 jako wartości domyślnej dla klucza
                    variant={isSelected ? (isCorrect ? "default" : "destructive") : "outline"}
                    onClick={() => {
                      if (userAnswers[currentQuestionIndex]?.selected_answer_id === null) {
                        // Upewnij się, że answer.id jest liczbą
                        handleAnswerSelect(answer.id || 0) // Użyj 0 jako wartości domyślnej
                      }
                    }}
                    disabled={userAnswers[currentQuestionIndex]?.selected_answer_id !== null}
                    size="sm"
                    className="w-full flex items-center justify-center space-x-1"
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
              onClick={() => setCurrentQuestionIndex(Math.max(currentQuestionIndex - 1, 0))}
              disabled={currentQuestionIndex === 0}
              variant="ghost"
              size="sm"
              className="flex items-center space-x-1"
            >
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">{t("previous")}</span>
            </Button>
            <div className="flex space-x-1">
              <Button
                variant="default"
                onClick={() => {
                  if (userAnswers[currentQuestionIndex]?.selected_answer_id !== null) {
                    if (currentQuestionIndex < selectedQuestions.length - 1) {
                      setCurrentQuestionIndex(currentQuestionIndex + 1)
                    } else {
                      setIsExamCompleted(true)
                    }
                  }
                }}
                disabled={userAnswers[currentQuestionIndex]?.selected_answer_id === null}
                size="sm"
                className="flex items-center space-x-1"
              >
                <span className="text-xs">
                  {currentQuestionIndex < selectedQuestions.length - 1 ? t("next") : t("finish")}
                </span>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
          {isSubmitting && (
            <div className="flex items-center justify-center space-x-1 mt-4">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-xs">{t("submitting_results")}</span>
            </div>
          )}
          {submitError && (
            <p className="text-xs md:text-sm text-destructive mt-4">
              {t("error_submitting_results")}: {submitError}
            </p>
          )}
          <div className="flex justify-center space-x-2 mt-4">
            <Button onClick={handleRestart} variant="default" size="sm" className="flex items-center space-x-1">
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">{t("restart_exam")}</span>
            </Button>
            <Button
              variant="secondary"
              onClick={submitExamResult}
              disabled={isSubmitting || answeredQuestions.length === 0}
              size="sm"
              className="flex items-center space-x-1"
            >
              <span className="text-xs">{t("save_attempt")}</span>
            </Button>
            <Button variant="destructive" onClick={onExit} size="sm" className="flex items-center space-x-1">
              <XCircle className="h-4 w-4" />
              <span className="text-xs">{t("exit_study")}</span>
            </Button>
          </div>
        </div>
      </div>
      {/* Obsługa chatu */}
      {isChatOpen && (
        <div className="fixed top-0 left-0 w-full h-full md:w-[40%] md:right-0 md:left-auto bg-background md:border-l border-border z-50">
          {/* Przycisk zamykania dla mobile */}
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
