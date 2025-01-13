// src/types.ts

export interface ExamAnswer {
  id: number
  text: string
  is_correct: boolean
}

export interface ExamQuestion {
  id: number
  text: string
  answers: ExamAnswer[]
}

export interface Exam {
  id: number
  name: string
  description: string
  created_at: string
  questions: ExamQuestion[]
}

export interface Flashcard {
  id: number;
  question: string;
  answer: string;
  media_url?: string;
}

export interface Deck {
  id: number;
  name: string;
  description?: string;
  flashcards: Flashcard[];
}

