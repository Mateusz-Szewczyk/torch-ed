"use client"

import { useState, useEffect, useCallback, type MouseEvent } from "react"
import { EditExamDialog } from "@/components/EditExamDialog"
import { Button } from "@/components/ui/button"
import { PlusCircle, BookOpen, Loader2, Info, ChevronRight, MoreVertical, Edit2, Trash2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { CustomTooltip } from "@/components/CustomTooltip"
import { StudyExam } from "@/components/StudyExam"
import { useTranslation } from "react-i18next"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

interface ExamAnswer {
  id: number
  text: string
  is_correct: boolean
}

interface ExamQuestion {
  id: number
  text: string
  answers: ExamAnswer[]
}

interface Exam {
  id: number
  name: string
  description: string
  created_at: string
  conversation_id?: number
  questions: ExamQuestion[]
}

export default function ExamsPage() {
  const [exams, setExams] = useState<Exam[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [studyingExam, setStudyingExam] = useState<Exam | null>(null)
  const [openCollapsibles, setOpenCollapsibles] = useState<{ [key: number]: boolean }>({})

  const { t } = useTranslation()

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

  const toggleCollapsible = (examId: number) => {
    setOpenCollapsibles((prev) => ({
      ...prev,
      [examId]: !prev[examId],
    }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="mr-2 h-16 w-16 animate-spin text-primary" />
        <span className="text-2xl font-semibold text-primary">{t("loading_exams")}</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl font-bold text-destructive">{t("error")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg">{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchExams} className="w-full">
              {t("try_again")}
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  if (studyingExam) {
    return <StudyExam exam={studyingExam} onExit={handleExitStudy} />
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-primary mb-2">{t("tests")}</h1>
        <CustomTooltip content={t("tests_tooltip")}>
          <Button variant="ghost" size="sm" className="rounded-full">
            <Info className="h-5 w-5" />
            <span className="sr-only">{t("more_information")}</span>
          </Button>
        </CustomTooltip>
      </div>

      {exams.length === 0 ? (
        <Card className="w-full max-w-2xl mx-auto">
          <CardHeader>
            <CardTitle className="text-2xl font-bold">{t("welcome_tests")}</CardTitle>
            <CardDescription>{t("get_started_create_test")}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center space-y-6 py-8">
            <BookOpen className="h-24 w-24 text-muted-foreground" />
            <p className="text-center text-muted-foreground">{t("no_tests_available")}</p>
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
      ) : (
        <>
          {/* Button for creating a new exam */}
          <div className="mb-8 flex justify-end">
            <EditExamDialog
              exam={{ id: 0, name: "", description: "", created_at: "", questions: [] }}
              onSave={handleSave}
              trigger={
                <Button className="w-full sm:w-auto" variant="default">
                  <PlusCircle className="h-5 w-5 mr-2" />
                  {t("create_new_test")}
                </Button>
              }
            />
          </div>
          {/* Exams grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {exams.map((exam) => (
              <div key={exam.id} className="relative group">
                <Card
                  className="flex flex-col w-full transition-all duration-300 ease-in-out hover:shadow-xl hover:-translate-y-1 group-hover:z-10 min-h-[300px] sm:min-h-[400px] max-h-[400px]"
                >
                  <CardHeader className="flex-shrink-0">
                    <div className="flex justify-between items-center">
                      <CardTitle className="text-xl font-bold truncate">{exam.name}</CardTitle>
                      <Collapsible
                        open={openCollapsibles[exam.id] || false}
                        onOpenChange={() => toggleCollapsible(exam.id)}
                      >
                        <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm" className="p-1" aria-label="Options">
                            <MoreVertical className="h-5 w-5" />
                          </Button>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="absolute right-2 sm:right-4 top-10 sm:top-12 bg-card border border-border rounded-md shadow-lg z-50 p-2">
                          <div className="flex flex-col">
                            <EditExamDialog
                              exam={exam}
                              onSave={handleSave}
                              trigger={
                                <Button variant="ghost" size="sm" className="justify-start">
                                  <Edit2 className="h-4 w-4 mr-2" />
                                  {t("edit")}
                                </Button>
                              }
                            />
                            <Button
                              variant="ghost"
                              size="sm"
                              className="justify-start text-destructive"
                              onClick={(e: MouseEvent<HTMLButtonElement>) => {
                                e.stopPropagation()
                                handleDelete(exam.id)
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t("delete")}
                            </Button>
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    </div>
                  </CardHeader>
                  <CardContent className="flex-grow overflow-hidden">
                    <p className="text-sm text-muted-foreground">{exam.description || t("no_description")}</p>
                  </CardContent>
                  <CardFooter className="mt-auto">
                    <Button variant="default" onClick={() => handleStudy(exam)} className="w-full flex items-center justify-between">
                      {t("study")}
                      <ChevronRight className="h-5 w-5 ml-2" />
                    </Button>
                  </CardFooter>
                </Card>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
