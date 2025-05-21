"use client"

import type React from "react"

import { useState } from "react"
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import type { Exam, ExamQuestion, ExamAnswer } from "@/types"
import { Trash2, Plus, Check, X } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"

interface EditExamDialogProps {
  exam: Exam
  onSave?: (updatedExam: Exam) => void
  trigger: React.ReactNode
}

export function EditExamDialog({ exam, onSave, trigger }: EditExamDialogProps) {
  const [formData, setFormData] = useState<Exam>({ ...exam })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"
  const EXAMS_API_BASE = `${API_BASE_URL}/exams/`

  const handleChange = (field: keyof Exam, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleQuestionChange = (questionIndex: number, field: keyof ExamQuestion, value: string) => {
    setFormData((prev) => {
      const updatedQuestions = [...prev.questions]
      updatedQuestions[questionIndex] = {
        ...updatedQuestions[questionIndex],
        [field]: value,
      }
      return { ...prev, questions: updatedQuestions }
    })
  }

  const handleAnswerChange = <T extends keyof ExamAnswer>(
    questionIndex: number,
    answerIndex: number,
    field: T,
    value: ExamAnswer[T],
  ) => {
    setFormData((prev) => {
      const updatedQuestions = [...prev.questions]
      const updatedAnswers = [...updatedQuestions[questionIndex].answers]
      updatedAnswers[answerIndex] = {
        ...updatedAnswers[answerIndex],
        [field]: value,
      }
      updatedQuestions[questionIndex] = {
        ...updatedQuestions[questionIndex],
        answers: updatedAnswers,
      }
      return { ...prev, questions: updatedQuestions }
    })
  }

  const addQuestion = () => {
    setFormData((prev) => ({
      ...prev,
      questions: [
        ...prev.questions,
        {
          id: 0, // New question will get an ID from the server
          text: "",
          answers: [
            { id: 0, text: "", is_correct: false },
            { id: 0, text: "", is_correct: false },
          ],
        },
      ],
    }))
  }

  const removeQuestion = (questionIndex: number) => {
    setFormData((prev) => {
      const updatedQuestions = [...prev.questions]
      updatedQuestions.splice(questionIndex, 1)
      return { ...prev, questions: updatedQuestions }
    })
  }

  const addAnswer = (questionIndex: number) => {
    setFormData((prev) => {
      const updatedQuestions = [...prev.questions]
      updatedQuestions[questionIndex] = {
        ...updatedQuestions[questionIndex],
        answers: [...updatedQuestions[questionIndex].answers, { id: 0, text: "", is_correct: false }],
      }
      return { ...prev, questions: updatedQuestions }
    })
  }

  const removeAnswer = (questionIndex: number, answerIndex: number) => {
    setFormData((prev) => {
      const updatedQuestions = [...prev.questions]
      const updatedAnswers = [...updatedQuestions[questionIndex].answers]
      updatedAnswers.splice(answerIndex, 1)
      updatedQuestions[questionIndex] = {
        ...updatedQuestions[questionIndex],
        answers: updatedAnswers,
      }
      return { ...prev, questions: updatedQuestions }
    })
  }

  const handleSave = async () => {
    setLoading(true)
    setError(null)

    // Validate form
    if (!formData.name.trim()) {
      setError("Nazwa egzaminu jest wymagana")
      setLoading(false)
      return
    }

    if (formData.questions.length === 0) {
      setError("Egzamin musi zawierać co najmniej jedno pytanie")
      setLoading(false)
      return
    }

    for (let i = 0; i < formData.questions.length; i++) {
      const question = formData.questions[i]
      if (!question.text.trim()) {
        setError(`Pytanie ${i + 1} nie może być puste`)
        setLoading(false)
        return
      }

      if (!question.answers.some((a) => a.is_correct)) {
        setError(`Pytanie ${i + 1} musi mieć co najmniej jedną poprawną odpowiedź`)
        setLoading(false)
        return
      }

      for (let j = 0; j < question.answers.length; j++) {
        if (!question.answers[j].text.trim()) {
          setError(`Odpowiedź ${j + 1} w pytaniu ${i + 1} nie może być pusta`)
          setLoading(false)
          return
        }
      }
    }

    try {
      // Let the parent component handle the API call
      if (onSave) {
        onSave(formData)
        setOpen(false)
      } else {
        // Fallback if onSave is not provided
        const payload = {
          name: formData.name,
          description: formData.description,
          questions: formData.questions.map((q) => ({
            id: q.id,
            text: q.text,
            answers: q.answers.map((a) =>
              a.id ? { id: a.id, text: a.text, is_correct: a.is_correct } : { text: a.text, is_correct: a.is_correct },
            ),
          })),
          conversation_id: formData.conversation_id || 0,
        }

        const res = await fetch(formData.id === 0 ? EXAMS_API_BASE : `${EXAMS_API_BASE}${formData.id}/`, {
          method: formData.id === 0 ? "POST" : "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })

        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || "Błąd zapisu egzaminu.")
        }

      }
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message)
      else setError("Nieznany błąd przy zapisie egzaminu.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Edytuj egzamin</h2>

          <div className="space-y-2">
            <label className="block font-medium">Nazwa</label>
            <input
              type="text"
              className="w-full border p-2 rounded"
              value={formData.name}
              onChange={(e) => handleChange("name", e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label className="block font-medium">Opis</label>
            <textarea
              className="w-full border p-2 rounded"
              value={formData.description}
              onChange={(e) => handleChange("description", e.target.value)}
            />
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium">Pytania</h3>
              <Button onClick={addQuestion} size="sm" variant="outline" className="flex items-center gap-1">
                <Plus className="w-4 h-4" /> Dodaj pytanie
              </Button>
            </div>

            <Accordion type="multiple" className="w-full">
              {formData.questions.map((question, qIndex) => (
                <AccordionItem key={qIndex} value={`question-${qIndex}`}>
                  <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center justify-between w-full pr-4">
                      <span className="text-left font-medium">
                        {question.text ? question.text : `Pytanie ${qIndex + 1}`}
                      </span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <Card className="border-0 shadow-none">
                      <CardContent className="p-4 space-y-4">
                        <div className="flex items-start gap-2">
                          <div className="flex-1">
                            <label className="block font-medium mb-1">Treść pytania</label>
                            <textarea
                              className="w-full border p-2 rounded"
                              value={question.text}
                              onChange={(e) => handleQuestionChange(qIndex, "text", e.target.value)}
                              rows={2}
                            />
                          </div>
                          <Button
                            variant="destructive"
                            size="icon"
                            onClick={() => removeQuestion(qIndex)}
                            className="mt-6"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <label className="block font-medium">Odpowiedzi</label>
                            <Button
                              onClick={() => addAnswer(qIndex)}
                              size="sm"
                              variant="outline"
                              className="flex items-center gap-1"
                            >
                              <Plus className="w-4 h-4" /> Dodaj odpowiedź
                            </Button>
                          </div>

                          <div className="space-y-2 mt-2">
                            {question.answers.map((answer, aIndex) => (
                              <div key={aIndex} className="flex items-center gap-2 p-2 border rounded bg-background">
                                <div className="flex items-center gap-2 flex-1">
                                  <Switch
                                    id={`correct-${qIndex}-${aIndex}`}
                                    checked={answer.is_correct}
                                    onCheckedChange={(checked) =>
                                      handleAnswerChange(qIndex, aIndex, "is_correct", checked)
                                    }
                                  />
                                  <Label htmlFor={`correct-${qIndex}-${aIndex}`} className="flex items-center gap-1">
                                    {answer.is_correct ? (
                                      <Check className="w-4 h-4 text-green-500" />
                                    ) : (
                                      <X className="w-4 h-4 text-red-500" />
                                    )}
                                    <span className="text-xs font-normal">
                                      {answer.is_correct ? "Poprawna" : "Niepoprawna"}
                                    </span>
                                  </Label>
                                </div>
                                <input
                                  type="text"
                                  className="flex-1 border p-2 rounded w-full"
                                  value={answer.text}
                                  onChange={(e) => handleAnswerChange(qIndex, aIndex, "text", e.target.value)}
                                  placeholder="Treść odpowiedzi"
                                />
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => removeAnswer(qIndex, aIndex)}
                                  disabled={question.answers.length <= 2}
                                  className="text-red-500 hover:text-red-700"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>

            {formData.questions.length === 0 && (
              <div className="text-center p-4 border rounded bg-muted/20">
                <p className="text-muted-foreground">Brak pytań. Dodaj pierwsze pytanie, aby kontynuować.</p>
              </div>
            )}
          </div>

          {error && <p className="text-red-500">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button onClick={() => setOpen(false)} variant="secondary">
              Anuluj
            </Button>
            <Button onClick={handleSave} disabled={loading}>
              {loading ? "Zapisuję..." : "Zapisz"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
