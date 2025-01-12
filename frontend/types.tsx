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

export interface Message {
  id: number;
  conversation_id: number;
  text: string;
  sender: 'user' | 'bot';
  created_at: string;
  isNew?: boolean;
  isError?: boolean;
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


export interface UserFlashcard {
  id: number;
  flashcard: Flashcard;
  ef: number;
  interval: number;
  repetitions: number;
  next_review: string;
}


export interface StudySession {
  id: number;
  user_id: string;
  deck_id: number;
  started_at: string;
  completed_at?: string;
}

export interface StudyRecord {
  id: number;
  session_id: number;
  user_flashcard_id: number;
  rating?: number;
  reviewed_at: string;
}