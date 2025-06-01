// types.ts

export interface ExamAnswer {
  id?: number;
  text: string;
  is_correct: boolean;
  question_id?: number;
}

export interface ExamQuestion {
  id?: number;
  text: string;
  exam_id?: number;
  answers: ExamAnswer[];
}

export interface Exam {
  id: number;
  name: string;
  description: string;
  created_at: string;
  user_id: number;
  conversation_id?: number;
  questions: ExamQuestion[];
  // Sharing related fields
  is_template?: boolean;
  template_id?: number;
  is_shared?: boolean;
  is_own?: boolean;
  original_exam_id?: number;
  added_at?: string;
  code_used?: string;
  access_type?: 'owner' | 'shared';
}

export interface ExamInfo {
  id: number;
  name: string;
  description: string;
  created_at: string;
  user_id: number;
  conversation_id?: number;
  question_count: number;
  // Sharing related fields
  is_template?: boolean;
  template_id?: number;
  is_shared?: boolean;
  is_own?: boolean;
  original_exam_id?: number;
  added_at?: string;
  code_used?: string;
  access_type?: 'owner' | 'shared';
}

export interface Flashcard {
  id: number;
  question: string;
  answer: string;
  media_url?: string;
  repetitions?: number | undefined;
  deck_id?: number;
}

export interface DeckInfo {
  access_type: string;
  id: number;
  user_id: number;
  name: string;
  description?: string;
  conversation_id: number;
  flashcard_count: number;
  created_at: string;
  last_session?: string;
  is_template?: boolean;
  template_id?: number;
  is_shared?: boolean;
  is_own?: boolean;
  original_deck_id?: number;
  added_at?: string;
  code_used?: string;
}

export interface Deck {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  flashcards: Flashcard[];
  conversation_id?: number;
  // Sharing related fields
  is_template?: boolean;
  template_id?: number;
}

// Sharing related types
export interface ShareableContent {
  id: number;
  share_code: string;
  content_type: 'deck' | 'exam';
  content_id: number;
  creator_id: number;
  is_public: boolean;
  created_at: string;
  access_count: number;
}

export interface ShareCodeInfo {
  content_id: number;
  name: string;
  description: string;
  creator_name: string;
  created_at: string;
  access_count: number;
  item_count: number;
  content_type: 'deck' | 'exam';
  already_added?: boolean;
  is_own_deck?: boolean;
  is_own_exam?: boolean;
}

export interface SharedDeck {
  user_deck_id: number;
  original_deck_id: number;
  deck_name: string;
  original_deck_name: string;
  flashcard_count: number;
  added_at: string;
  code_used: string;
}

export interface SharedExam {
  user_exam_id: number;
  original_exam_id: number;
  exam_name: string;
  original_exam_name: string;
  question_count: number;
  added_at: string;
  code_used: string;
}

export interface MySharedCode {
  share_code: string;
  content_type: 'deck' | 'exam';
  content_id: number;
  content_name: string;
  item_count: number;
  created_at: string;
  access_count: number;
  deck_name?: string; // For backward compatibility
  flashcard_count?: number; // For backward compatibility
}

export interface ShareStatistics {
  created_share_codes?: number;
  created_deck_codes?: number;
  created_exam_codes?: number;
  added_shared_decks?: number;
  added_shared_exams?: number;
  total_deck_accesses?: number;
  total_exam_accesses?: number;
  total_created_codes?: number;
  total_added_content?: number;
}

// API Response types
export interface ShareCodeResponse {
  success: boolean;
  share_code: string;
  deck_name?: string;
  exam_name?: string;
  message: string;
}

export interface AddByCodeResponse {
  success: boolean;
  message: string;
  deck_id?: number;
  exam_id?: number;
  deck_name?: string;
  exam_name?: string;
}

export interface DeactivateCodeResponse {
  success: boolean;
  message: string;
}

export interface RemoveSharedContentResponse {
  success: boolean;
  message: string;
}

// Existing types (updated)
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

// Exam results types
export interface ExamResultAnswer {
  id?: number;
  exam_result_id?: number;
  question_id: number;
  selected_answer_id: number;
  is_correct?: boolean;
  answer_time?: number;
}

export interface ExamResult {
  id?: number;
  exam_id: number;
  user_id?: number;
  score?: number;
  started_at?: string;
  completed_at?: string;
  answers: ExamResultAnswer[];
}

export interface ExamResultCreate {
  exam_id: number;
  answers: ExamResultAnswer[];
}

export interface ExamResultRead {
  id: number;
  exam_id: number;
  user_id: number;
  score: number;
  started_at: string;
  completed_at: string;
  answers: ExamResultAnswer[];
}

// Study session types
export interface StudySessionResponse {
  study_session_id: number | null;
  available_cards: Flashcard[];
  next_session_date: string | null;
}

export interface StudyDeckProps {
  deck: Deck;
  study_session_id: number | null;
  available_cards: Flashcard[];
  next_session_date: string | null;
  conversation_id: number;
  onExit: () => void;
}

// User types
export interface User {
  id_: number;
  user_name: string;
  email: string;
  role: string;
  age?: number;
  confirmed: boolean;
}

// Conversation types
export interface Conversation {
  id: number;
  user_id: number;
  title?: string;
  created_at: string;
}
