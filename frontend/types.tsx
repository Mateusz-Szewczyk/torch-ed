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
  conversation_id: number;
}

export interface ErrorDetail {
  loc: string[];
  msg: string;
  type: string;
}

export interface ErrorResponse {
  detail: string | ErrorDetail[];
}

export interface BulkRecordRating {
  flashcard_id: number;
  rating: number;
  answered_at: string; // ISO string
}

export interface BulkRecordRequest {
  session_id: number;
  deck_id: number;
  ratings: BulkRecordRating[];
}

export interface BulkRecordResponse {
  message: string;
}