// src/components/StudyExam.tsx

'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useTranslation } from 'react-i18next';
import { ChevronRight, ChevronLeft, CheckCircle, XCircle, MessageCircle } from 'lucide-react';
import * as Slider from '@radix-ui/react-slider';
import Chat from '@/components/Chat'; // <-- import czatu
import { Loader2 } from 'lucide-react'; // Dodaj import Loader2

interface Answer {
  id: number;
  text: string;
  is_correct: boolean;
}

interface Question {
  id: number;
  text: string;
  answers: Answer[];
}

interface Exam {
  id: number; // Dodaj identyfikator egzaminu
  name: string;
  description: string;
  questions: Question[];
}

interface StudyExamProps {
  exam: Exam;
  onExit: () => void;
}

interface ExamResultAnswerCreate {
  question_id: number;
  selected_answer_id: number;
  answer_time: string; // ISO string
}

interface ExamResultCreate {
  exam_id: number;
  answers: ExamResultAnswerCreate[];
}

interface ExamResultRead {
  id: number;
  exam_id: number;
  user_id: string;
  started_at: string;
  completed_at: string | null;
  score: number | null;
  answers: ExamResultAnswerRead[];
}

interface ExamResultAnswerRead {
  id: number;
  question_id: number;
  selected_answer_id: number;
  is_correct: boolean;
  answer_time: string;
}

export function StudyExam({ exam, onExit }: StudyExamProps) {
  const { t } = useTranslation();

  const [conversationId] = useState<number>(999);

  // Czy panel czatu jest otwarty
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);

  // Stan egzaminu
  const [numQuestions, setNumQuestions] = useState<number>(10);
  const [isSelectionStep, setIsSelectionStep] = useState<boolean>(true);
  const [selectedQuestions, setSelectedQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [score, setScore] = useState<number>(0);
  const [userAnswers, setUserAnswers] = useState<{
    question_id: number;
    selected_answer_id: number;
    answer_time: string;
  }[]>([]);
  const [isExamCompleted, setIsExamCompleted] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';

  // Funkcja losująca pytania
  const selectRandomQuestions = (allQuestions: Question[], count: number): Question[] => {
    const shuffled = [...allQuestions].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, count);
  };

  // Obsługa slidera
  const handleSliderChange = (values: number[]) => {
    setNumQuestions(values[0]);
  };

  // Obsługa inputa tekstowego
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value)) {
      const clampedValue = Math.min(Math.max(value, 1), exam.questions.length);
      setNumQuestions(clampedValue);
    }
  };

  // Start egzaminu
  const startExam = () => {
    const questions = selectRandomQuestions(exam.questions, numQuestions);
    setSelectedQuestions(questions);
    setUserAnswers(Array(questions.length).fill(null));
    setIsSelectionStep(false);
  };

  // Odpowiedź na pytanie
  const handleAnswerSelect = (answerId: number) => {
    const currentQuestion = selectedQuestions[currentQuestionIndex];
    const selectedAnswer = currentQuestion.answers.find(a => a.id === answerId);

    const answerTime = new Date().toISOString(); // Zapisz czas odpowiedzi

    const updatedUserAnswers = [...userAnswers];
    updatedUserAnswers[currentQuestionIndex] = {
      question_id: currentQuestion.id,
      selected_answer_id: answerId,
      answer_time: answerTime,
    };
    setUserAnswers(updatedUserAnswers);

    if (selectedAnswer && selectedAnswer.is_correct) {
      setScore(prevScore => prevScore + 1);
    }

    if (currentQuestionIndex < selectedQuestions.length - 1) {
      setCurrentQuestionIndex(prevIndex => prevIndex + 1);
    } else {
      setIsExamCompleted(true);
    }
  };

  const handleRestart = () => {
    setCurrentQuestionIndex(0);
    setScore(0);
    setUserAnswers(Array(selectedQuestions.length).fill(null));
    setIsExamCompleted(false);
    setIsSelectionStep(true);
  };

  // Funkcja do przesyłania wyników egzaminu
  const submitExamResult = async () => {
    const examResult: ExamResultCreate = {
      exam_id: exam.id,
      answers: userAnswers.map(answer => ({
        question_id: answer.question_id,
        selected_answer_id: answer.selected_answer_id,
        answer_time: answer.answer_time,
      })),
    };

    try {
      setIsSubmitting(true);
      setSubmitError(null);

      const response = await fetch(`${API_BASE_URL}/submit/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(examResult),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Błąd podczas przesyłania wyników egzaminu.');
      }

      const result: ExamResultRead = await response.json();
      console.log('Wynik egzaminu został zapisany:', result);

      // Opcjonalnie, możesz zaktualizować stan lub przekierować użytkownika
      alert('Wynik egzaminu został zapisany pomyślnie!');
    } catch (error: unknown) {
      if (error instanceof Error) {
        console.error('Error submitting exam result:', error.message);
        setSubmitError(error.message);
      } else {
        console.error('Unknown error submitting exam result');
        setSubmitError('Wystąpił nieznany błąd podczas przesyłania wyników egzaminu.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Wywołanie submitExamResult po zakończeniu egzaminu
  useEffect(() => {
    if (isExamCompleted) {
      submitExamResult();
    }
  }, [isExamCompleted]);

  // ---------------
  // RENDEROWANIE
  // ---------------

  // Krok 1: Wybór liczby pytań
  if (isSelectionStep) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <div className="bg-card p-8 rounded-lg shadow-md w-full max-w-md">
          {/* Przycisk Powrotu */}
          <div className="flex justify-end mb-4">
            <Button
              onClick={onExit}
              variant="ghost"
              className="flex items-center space-x-2"
            >
              <ChevronLeft className="h-5 w-5" />
              <span>{t('back')}</span>
            </Button>
          </div>
          <h2 className="text-2xl font-bold mb-4 text-primary text-center">
            {t('select_number_of_questions')}
          </h2>
          <div className="flex flex-col items-center">
            {/* Suwak */}
            <div className="w-full mb-4">
              <Slider.Root
                className="relative flex items-center select-none touch-none w-full h-6"
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
                <Slider.Thumb className="block w-4 h-4 bg-primary rounded-full shadow focus:outline-none focus:ring" />
              </Slider.Root>
            </div>
            {/* Input */}
            <div className="flex items-center space-x-2 mb-6">
              <span className="text-sm text-muted-foreground">
                {t('number_of_questions')}:
              </span>
              <input
                type="number"
                min={1}
                max={Math.min(exam.questions.length, 50)}
                value={numQuestions}
                onChange={handleInputChange}
                className="w-16 p-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            {/* Start Exam Button */}
            <Button
              onClick={startExam}
              variant="default"
              className="w-full flex items-center justify-center space-x-2"
            >
              <span>{t('start_exam')}</span>
              <ChevronRight className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Krok 2: Egzamin zakończony
  if (isExamCompleted) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-screen bg-background">
        <div className="bg-card p-8 rounded-lg shadow-md w-full max-w-2xl text-center">
          <h2 className="text-3xl font-bold mb-4 text-primary">
            {t('exam_summary')}
          </h2>
          <p className="text-xl mb-6 text-secondary">
            {t('you_scored')} {score} {t('out_of')} {selectedQuestions.length}
          </p>
          {/* Wskaźnik ładowania podczas przesyłania */}
          {isSubmitting && (
            <div className="flex items-center justify-center space-x-2 mb-4">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>{t('submitting_results')}</span>
            </div>
          )}
          {/* Komunikat o błędzie */}
          {submitError && (
            <p className="text-destructive mb-4">
              {t('error_submitting_results')}: {submitError}
            </p>
          )}
          <div className="flex justify-center space-x-4">
            <Button
              onClick={handleRestart}
              variant="default"
              className="flex items-center space-x-2"
            >
              <ChevronLeft className="h-5 w-5" />
              <span>{t('restart_exam')}</span>
            </Button>
            <Button
              variant="destructive"
              onClick={onExit}
              className="flex items-center space-x-2"
            >
              <XCircle className="h-5 w-5" />
              <span>{t('exit')}</span>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Krok 3: Rozwiązywanie egzaminu
  const currentQuestion = selectedQuestions[currentQuestionIndex];

  return (
    <div className="h-screen w-full bg-background flex items-center justify-center">
      {/* Kontener główny */}
      <div className="relative flex w-full h-full items-center justify-center">
        {/* Okno egzaminu */}
        <div
          className={`transition-all duration-300 ${
            isChatOpen ? 'mr-96' : ''
          } w-full max-w-2xl p-4`}
        >
          <div className="bg-card p-6 rounded-lg shadow-md w-full h-auto">
            {/* Nagłówek */}
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-primary">{exam.name}</h2>
              {/* Przycisk toggle czatu */}
              <Button
                variant="secondary"
                onClick={() => setIsChatOpen(!isChatOpen)}
                className="flex items-center space-x-2"
              >
                <MessageCircle className="h-5 w-5" />
                <span>
                  {isChatOpen ? t('hide_chat') : t('show_chat')}
                </span>
              </Button>
            </div>

            <p className="mb-6">{exam.description}</p>
            {/* Wyświetlanie pytania */}
            <div className="mb-4">
              <h3 className="text-xl font-semibold mb-2">
                {t('question')}: {currentQuestion.text}
              </h3>
              <div className="grid grid-cols-1 gap-4">
                {currentQuestion.answers.map((answer) => {
                  const isSelected =
                    userAnswers[currentQuestionIndex]?.selected_answer_id === answer.id;
                  const isCorrect = answer.is_correct;

                  return (
                    <Button
                      key={answer.id}
                      variant={
                        isSelected
                          ? isCorrect
                            ? 'default'
                            : 'destructive'
                          : 'outline'
                      }
                      onClick={() => {
                        if (userAnswers[currentQuestionIndex] === undefined) {
                          handleAnswerSelect(answer.id);
                        }
                      }}
                      disabled={userAnswers[currentQuestionIndex] !== undefined}
                      className="w-full flex items-center justify-center space-x-2"
                    >
                      {isSelected && isCorrect && (
                        <CheckCircle className="h-5 w-5 text-success" />
                      )}
                      {isSelected && !isCorrect && (
                        <XCircle className="h-5 w-5 text-destructive" />
                      )}
                      <span>{answer.text}</span>
                    </Button>
                  );
                })}
              </div>
            </div>
            {/* Nawigacja pytaniami */}
            <div className="flex justify-between mt-6">
              <Button
                onClick={() =>
                  setCurrentQuestionIndex(Math.max(currentQuestionIndex - 1, 0))
                }
                disabled={currentQuestionIndex === 0}
                variant="ghost"
                className="flex items-center space-x-2"
              >
                <ChevronLeft className="h-5 w-5" />
                <span>{t('previous')}</span>
              </Button>
              <Button
                variant="default"
                onClick={() => {
                  if (userAnswers[currentQuestionIndex] !== undefined) {
                    if (currentQuestionIndex < selectedQuestions.length - 1) {
                      setCurrentQuestionIndex(currentQuestionIndex + 1);
                    } else {
                      setIsExamCompleted(true);
                    }
                  }
                }}
                disabled={userAnswers[currentQuestionIndex] === undefined}
                className="flex items-center space-x-2"
              >
                <span>
                  {currentQuestionIndex < selectedQuestions.length - 1
                    ? t('next')
                    : t('finish')}
                </span>
                <ChevronRight className="h-5 w-5" />
              </Button>
            </div>
            {/* Wyjście z egzaminu */}
            <Button
              variant="destructive"
              onClick={onExit}
              className="mt-6 w-full flex items-center justify-center space-x-2"
            >
              <XCircle className="h-5 w-5" />
              <span>{t('exit_study')}</span>
            </Button>
          </div>
        </div>

        {/* Panel czatu po prawej stronie */}
        {isChatOpen && (
          <div className="w-[40rem] h-full fixed right-0 top-0 bg-background border-l border-border z-50">
            <Chat conversationId={conversationId} />
          </div>
        )}
      </div>
    </div>
  );
}
