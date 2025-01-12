// src/components/StudyDeck.tsx

'use client';

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, RotateCcw, MessageCircle, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import Chat from '@/components/Chat';
import Image from 'next/image';
import { Flashcard, Deck, StudySession, StudyRecord, UserFlashcard } from '@/types';
import { fetchJson } from '@/utils/fetchJson';

interface StudyDeckProps {
  deck: Deck;
  onExit: () => void;
}

// Pobieramy z env:
const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8000/api';

export function StudyDeck({ deck, onExit }: StudyDeckProps) {
  const { t } = useTranslation();

  // Stan sesji nauki
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [currentFlashcard, setCurrentFlashcard] = useState<Flashcard | null>(null);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Conversation ID dla czatu
  const conversationId = deck.id;

  // Inicjalizacja sesji nauki
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const response = await fetchJson<StudySession>(`${API_BASE_URL}/study_sessions/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ deck_id: deck.id }),
        });
        setSessionId(response.id);
        fetchNextFlashcard(response.id);
      } catch (error) {
        if (error instanceof Error) {
          console.error('Błąd podczas inicjalizacji sesji nauki:', error.message);
        } else {
          console.error('Nieznany błąd podczas inicjalizacji sesji nauki:', error);
        }
      }
    };

    initializeSession();
  }, [deck.id]);

  // Funkcja do pobrania następnej fiszki
  const fetchNextFlashcard = async (sessionId: number) => {
    try {
      const flashcard = await fetchJson<Flashcard>(`${API_BASE_URL}/study_sessions/next_flashcard/${sessionId}/`, {
        method: 'GET',
      });
      setCurrentFlashcard(flashcard);
      setIsFlipped(false);
    } catch (error) {
      if (error instanceof Error) {
        console.error('Błąd podczas pobierania następnej fiszki:', error.message);
      } else {
        console.error('Nieznany błąd podczas pobierania następnej fiszki:', error);
      }
      setCurrentFlashcard(null);
    }
  };

  // Funkcja do rejestrowania oceny
  const recordReview = async (rating: number) => {
    if (!sessionId || !currentFlashcard) return;

    try {
      setIsSubmitting(true);
      setSubmitError(null);

      // Pobierz UserFlashcard ID dla bieżącej fiszki
      const userFlashcard = await fetchJson<UserFlashcard>(`${API_BASE_URL}/user_flashcards/by_flashcard/${currentFlashcard.id}/`, {
        method: 'GET',
      });

      await fetchJson<StudyRecord>(`${API_BASE_URL}/study_sessions/record_review/${sessionId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_flashcard_id: userFlashcard.id,
          rating: rating,
        }),
      });

      // Pobierz następną fiszkę
      fetchNextFlashcard(sessionId);
    } catch (error) {
      if (error instanceof Error) {
        console.error('Błąd podczas rejestrowania przeglądu:', error.message);
        setSubmitError(error.message);
      } else {
        console.error('Nieznany błąd podczas rejestrowania przeglądu:', error);
        setSubmitError('Błąd podczas zapisywania przeglądu.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Funkcja do resetowania sesji nauki
  const resetSession = async () => {
    if (!sessionId) return;

    try {
      setIsSubmitting(true);
      setSubmitError(null);
      // Tworzenie nowej sesji
      const response = await fetchJson<StudySession>(`${API_BASE_URL}/study_sessions/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ deck_id: deck.id }),
      });
      setSessionId(response.id);
      fetchNextFlashcard(response.id);
    } catch (error) {
      if (error instanceof Error) {
        console.error('Błąd podczas resetowania sesji nauki:', error.message);
        setSubmitError(error.message);
      } else {
        console.error('Nieznany błąd podczas resetowania sesji nauki:', error);
        setSubmitError('Błąd podczas resetowania sesji nauki.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Flipping flashcard
  const handleFlip = () => {
    setIsFlipped(!isFlipped);
  };

  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p>{t('initializing_study_session')}</p>
      </div>
    );
  }

  if (!currentFlashcard) {
    return (
      <div className="h-screen flex items-center justify-center bg-background p-4">
        <div className="flex flex-col items-center justify-center space-y-4">
          <h2 className="text-2xl font-bold">{t('congratulations')}</h2>
          <p>{t('completed_flashcards')}</p>
          <div className="flex space-x-4">
            <Button onClick={resetSession} disabled={isSubmitting}>
              <RotateCcw className="mr-2 h-4 w-4" />
              {t('reset_deck')}
            </Button>
            <Button onClick={onExit} variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t('back_to_decks')}
            </Button>
          </div>
          {isSubmitting && (
            <div className="flex items-center space-x-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>{t('saving_results')}</span>
            </div>
          )}
          {submitError && (
            <p className="text-destructive">{submitError}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full bg-background flex items-center justify-center relative">
      {/* Okno talii - przesuwa się w lewo, gdy chat jest otwarty */}
      <div
        className={`transition-all duration-300 ${
          isChatOpen ? 'mr-[40rem]' : ''
        } w-full max-w-md flex flex-col min-h-[80vh] bg-card shadow-md rounded-lg`}
      >
        {/* Header */}
        <div className="p-4 flex justify-between items-center border-b border-border">
          <Button onClick={onExit} variant="ghost" className="flex items-center space-x-2">
            <ArrowLeft className="h-4 w-4" />
            <span>{t('exit_study')}</span>
          </Button>
          {/* Przycisk toggle czatu */}
          <Button
            variant="secondary"
            onClick={() => setIsChatOpen(!isChatOpen)}
            className="flex items-center space-x-2"
          >
            <MessageCircle className="h-5 w-5" />
            <span>{isChatOpen ? t('hide_chat') : t('show_chat')}</span>
          </Button>
        </div>

        {/* Zawartość talii */}
        <div className="flex-grow flex flex-col items-center justify-center p-4 space-y-4">
          <div className="mb-4 text-sm font-medium text-primary">
            {t('flashcard_counter', {
              current: 1, // Możesz dynamicznie aktualizować to pole
              total: deck.flashcards.length
            })}
          </div>

          <div className="w-80 h-64 [perspective:1000px]">
            <Card
              className={`w-full h-full cursor-pointer transition-transform duration-700 [transform-style:preserve-3d] ${
                isFlipped ? '[transform:rotateY(180deg)]' : ''
              }`}
              onClick={handleFlip}
            >
              {/* Front Side */}
              <CardContent className="absolute w-full h-full p-4 [backface-visibility:hidden] flex items-center justify-center">
                <div className="max-h-full w-full overflow-y-auto scrollbar-thin scrollbar-thumb-rounded scrollbar-track-transparent">
                  <p className="text-xl font-semibold text-center">{currentFlashcard.question}</p>
                  {currentFlashcard.media_url && (
                    <Image
                      src={currentFlashcard.media_url}
                      alt="Flashcard Media"
                      className="mt-4 max-w-full h-auto rounded shadow"
                      width={500}
                      height={300}
                      objectFit="contain"
                    />
                  )}
                </div>
              </CardContent>

              {/* Back Side */}
              <CardContent className="absolute w-full h-full p-4 [backface-visibility:hidden] [transform:rotateY(180deg)] flex items-center justify-center">
                <div className="max-h-full w-full overflow-y-auto scrollbar-thin scrollbar-thumb-rounded scrollbar-track-transparent">
                  <p className="text-xl font-semibold text-center">{currentFlashcard.answer}</p>
                  {currentFlashcard.media_url && (
                    <Image
                      src={currentFlashcard.media_url}
                      alt="Flashcard Media"
                      className="mt-4 max-w-full h-auto rounded shadow"
                      width={500}
                      height={300}
                      objectFit="contain"
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Rating Buttons */}
          <div className="h-20 flex justify-center items-center">
            {isFlipped && (
              <div className="flex space-x-4">
                <Button
                  onClick={() => recordReview(0)}
                  className="bg-red-500 hover:bg-red-600 text-white"
                >
                  {t('hard')}
                </Button>
                <Button
                  onClick={() => recordReview(3)}
                  className="bg-blue-300 hover:bg-blue-400 text-gray-800"
                >
                  {t('good')}
                </Button>
                <Button
                  onClick={() => recordReview(5)}
                  className="bg-green-500 hover:bg-green-600 text-white"
                >
                  {t('easy')}
                </Button>
              </div>
            )}
          </div>

          {/* Loading Indicator and Error Message */}
          {isSubmitting && (
            <div className="flex items-center space-x-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>{t('saving_review')}</span>
            </div>
          )}
          {submitError && (
            <p className="text-destructive">{submitError}</p>
          )}
        </div>
      </div>

      {/* Panel czatu z prawej strony */}
      {isChatOpen && (
        <div className="w-[40%] h-full fixed right-0 top-0 bg-background border-l border-border z-50">
          <Chat conversationId={conversationId} />
        </div>
      )}
    </div>
  );
}
