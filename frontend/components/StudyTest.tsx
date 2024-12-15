// components/StudyTest.tsx
'use client'

import React from 'react'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'

interface Test {
  id: number;
  name: string;
  description?: string;
  questions: Question[];
}

interface Question {
  id?: number;
  question: string;
  answer: string;
}

interface StudyTestProps {
  test: Test;
  onExit: () => void;
}

export function StudyTest({ test, onExit }: StudyTestProps) {
  const { t } = useTranslation()
  const [currentQuestionIndex, setCurrentQuestionIndex] = React.useState(0)
  const [showAnswer, setShowAnswer] = React.useState(false)

  const handleNext = () => {
    setShowAnswer(false)
    setCurrentQuestionIndex((prev) => prev + 1)
  }

  const handlePrev = () => {
    setShowAnswer(false)
    setCurrentQuestionIndex((prev) => Math.max(prev - 1, 0))
  }

  const currentQuestion = test.questions[currentQuestionIndex]

  return (
    <div className="p-8 flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-2xl">
        <h2 className="text-2xl font-bold mb-4">{test.name}</h2>
        <p className="mb-6">{test.description}</p>
        {currentQuestion ? (
          <div>
            <h3 className="text-xl font-semibold mb-2">
              {t('question')}: {currentQuestion.question}
            </h3>
            {showAnswer && (
              <p className="text-lg text-green-600 mb-4">
                {t('answer')}: {currentQuestion.answer}
              </p>
            )}
            <Button onClick={() => setShowAnswer(!showAnswer)} className="mb-4">
              {showAnswer ? t('hide_answer') : t('show_answer')}
            </Button>
            <div className="flex justify-between">
              <Button onClick={handlePrev} disabled={currentQuestionIndex === 0}>
                {t('previous')}
              </Button>
              <Button onClick={handleNext} disabled={currentQuestionIndex === test.questions.length - 1}>
                {t('next')}
              </Button>
            </div>
          </div>
        ) : (
          <p>{t('no_questions')}</p>
        )}
        <Button variant="destructive" onClick={onExit} className="mt-6 w-full">
          {t('exit_study')}
        </Button>
      </div>
    </div>
  )
}
