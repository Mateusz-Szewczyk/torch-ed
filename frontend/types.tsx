export interface ExamAnswer {
  id?: number;
  text: string;
  is_correct: boolean;
}

export interface ExamQuestion {
  id?: number;
  text: string;
  answers: ExamAnswer[];
}

export interface Exam {
  id: number;
  name: string;
  description: string;
  created_at: string;
  conversation_id?: number;
  questions: ExamQuestion[];
}

export interface Flashcard {
  id: number;
  question: string;
  answer: string;
  media_url?: string;
  repetitions?: number | undefined;
}

export interface DeckInfo {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  conversation_id: number;
  flashcard_count: number;
  created_at: string;
  last_session?: string;
}

export interface Deck {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  flashcards: Flashcard[];
  conversation_id?: number;
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
  answered_at: string;
}

export interface BulkRecordRequest {
  session_id: number;
  deck_id: number;
  ratings: BulkRecordRating[];
}

export interface BulkRecordResponse {
  message: string;
}
