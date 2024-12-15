// src/components/StudyExam.tsx
'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { Exam, ExamQuestion, ExamAnswer } from '../schemas'
import { ChevronRight, ChevronLeft, CheckCircle, XCircle } from 'lucide-react'

interface StudyExamProps {
  exam: Exam;
  onExit: () => void;
}

export function StudyExam({ exam, onExit }: StudyExamProps) {
  const { t } = useTranslation()
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0)
  const [score, setScore] = useState<number>(0)
  const [userAnswers, setUserAnswers] = useState<(number | null)[]>(Array(exam.questions.length).fill(null))
  const [isExamCompleted, setIsExamCompleted] = useState<boolean>(false)

  const handleAnswerSelect = (answerId: number) => {
    const currentQuestion = exam.questions[currentQuestionIndex]
    const selectedAnswer = currentQuestion.answers.find(a => a.id === answerId)

    // Aktualizacja odpowiedzi użytkownika
    const updatedUserAnswers = [...userAnswers]
    updatedUserAnswers[currentQuestionIndex] = answerId
    setUserAnswers(updatedUserAnswers)

    // Aktualizacja punktów
    if (selectedAnswer && selectedAnswer.is_correct) {
      setScore(score + 1)
    }

    // Przejście do następnego pytania lub zakończenie egzaminu
    if (currentQuestionIndex < exam.questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
    } else {
      setIsExamCompleted(true)
    }
  }

  const handleRestart = () => {
    setCurrentQuestionIndex(0)
    setScore(0)
    setUserAnswers(Array(exam.questions.length).fill(null))
    setIsExamCompleted(false)
  }

  if (isExamCompleted) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-screen bg-background">
        <div className="bg-card p-8 rounded-lg shadow-md w-full max-w-2xl text-center">
          <h2 className="text-3xl font-bold mb-4 text-primary">{t('exam_summary')}</h2>
          <p className="text-xl mb-6 text-secondary">{t('you_scored')} {score} {t('out_of')} {exam.questions.length}</p>
          <div className="flex justify-center space-x-4">
            <Button
              onClick={handleRestart}
              variant="default"
              color="primary"
              className="flex items-center space-x-2"
            >
              <ChevronLeft className="h-5 w-5" />
              <span>{t('restart_exam')}</span>
            </Button>
            <Button
              variant="destructive"
              onClick={onExit}
              color="destructive"
              className="flex items-center space-x-2"
            >
              <XCircle className="h-5 w-5" />
              <span>{t('exit')}</span>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  const currentQuestion = exam.questions[currentQuestionIndex]

  return (
    <div className="p-8 flex flex-col items-center justify-center min-h-screen bg-background">
      <div className="bg-card p-8 rounded-lg shadow-md w-full max-w-2xl">
        <h2 className="text-2xl font-bold mb-4 text-primary">{exam.name}</h2>
        <p className="mb-6">{exam.description}</p>
        <div className="mb-4">
          <h3 className="text-xl font-semibold mb-2">
            {t('question')}: {currentQuestion.text}
          </h3>
          <div className="grid grid-cols-1 gap-4">
            {currentQuestion.answers.map((answer: ExamAnswer) => {
              const isSelected = userAnswers[currentQuestionIndex] === answer.id
              const isCorrect = answer.is_correct

              return (
                <Button
                  key={answer.id}
                  variant={isSelected ? (isCorrect ? 'success' : 'destructive') : 'outline'}
                  color={isSelected ? (isCorrect ? 'green' : 'red') : 'primary'}
                  onClick={() => handleAnswerSelect(answer.id)}
                  disabled={userAnswers[currentQuestionIndex] !== null}
                  className="w-full flex items-center justify-center space-x-2"
                >
                  {isSelected && isCorrect && <CheckCircle className="h-5 w-5 text-success" />}
                  {isSelected && !isCorrect && <XCircle className="h-5 w-5 text-destructive" />}
                  <span>{answer.text}</span>
                </Button>
              )
            })}
          </div>
        </div>
        <div className="flex justify-between mt-6">
          <Button
            onClick={() => setCurrentQuestionIndex(Math.max(currentQuestionIndex - 1, 0))}
            disabled={currentQuestionIndex === 0}
            variant="ghost"
            color="primary"
            className="flex items-center space-x-2"
          >
            <ChevronLeft className="h-5 w-5" />
            <span>{t('previous')}</span>
          </Button>
          <Button
            variant="default"
            color="primary"
            onClick={() => {
              // Przejście do następnego pytania tylko jeśli użytkownik już odpowiedział
              if (userAnswers[currentQuestionIndex] !== null) {
                // Funkcja handleNext nie jest zdefiniowana, dlatego możemy użyć setCurrentQuestionIndex
                setCurrentQuestionIndex(currentQuestionIndex + 1)
              }
            }}
            disabled={userAnswers[currentQuestionIndex] === null}
            className="flex items-center space-x-2"
          >
            <span>{currentQuestionIndex < exam.questions.length - 1 ? t('next') : t('finish')}</span>
            <ChevronRight className="h-5 w-5" />
          </Button>
        </div>
        <Button
          variant="destructive"
          onClick={onExit}
          color="destructive"
          className="mt-6 w-full flex items-center justify-center space-x-2"
        >
          <XCircle className="h-5 w-5" />
          <span>{t('exit_study')}</span>
        </Button>
      </div>
    </div>
  )
}
