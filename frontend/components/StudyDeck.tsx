// src/components/StudyDeck.tsx

'use client';

import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, MessageCircle, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import Chat from '@/components/Chat';
import Image from 'next/image';
import { Flashcard, Deck } from '@/types';
import { fetchJson } from '@/utils/fetchJson';

// Struktura do przechowania ocen "hard/good/easy"
type LocalRating = {
  flashcardId: number;
  rating: number;       // 0=hard, 3=good, 5=easy
  answeredAt: string;   // ISO string
};

type CardSeenCount = {
  [flashcardId: number]: number; // ile razy user widział kartę
};

interface StudyDeckProps {
  deck: Deck;
  onExit: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8000/api';

export function StudyDeck({ deck, onExit }: StudyDeckProps) {
  const { t } = useTranslation();

  // Kolejka fiszek (front-end pętla)
  const [cardsQueue, setCardsQueue] = useState<Flashcard[]>([]);
  // Indeks aktualnego elementu w kolejce
  const [currentIndex, setCurrentIndex] = useState(0);

  // Ocenione fiszki (do hurtowego zapisu)
  const [localRatings, setLocalRatings] = useState<LocalRating[]>([]);

  // Ile razy user widział daną fiszkę (do statystyk / UI feedback)
  const [cardSeenCount, setCardSeenCount] = useState<CardSeenCount>({});

  // Stan flippingu
  const [isFlipped, setIsFlipped] = useState(false);
  // Stan otwarcia chatu
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Stan zapisu + ewentualny błąd
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // conversationId do czatu
  const conversationId = deck.id;

  // ---------------------------
  // 1. Inicjalizacja stanu z localStorage (lub z decku)
  // ---------------------------
  useEffect(() => {
    // Próbujemy wczytać stan kolejki i ocen z localStorage
    const savedQueue = localStorage.getItem(`deck-${deck.id}-queue`);
    const savedRatings = localStorage.getItem(`deck-${deck.id}-ratings`);
    const savedSeenCount = localStorage.getItem(`deck-${deck.id}-seenCount`);

    if (savedQueue && savedRatings && savedSeenCount) {
      try {
        const parsedQueue: Flashcard[] = JSON.parse(savedQueue);
        const parsedRatings: LocalRating[] = JSON.parse(savedRatings);
        const parsedSeenCount: CardSeenCount = JSON.parse(savedSeenCount);
        setCardsQueue(parsedQueue);
        setLocalRatings(parsedRatings);
        setCardSeenCount(parsedSeenCount);
        setCurrentIndex(0);
        return;
      } catch (e) {
        console.error('Error reading localStorage:', e);
      }
    }

    // Brak stanu => wypełniamy queue fiszkami z deck
    const queue = [...deck.flashcards];
    setCardsQueue(queue);
    setCardSeenCount(
      queue.reduce((obj, card) => {
        obj[card.id] = 0;
        return obj;
      }, {} as CardSeenCount)
    );
    setCurrentIndex(0);
  }, [deck]);

  // ---------------------------
  // 2. Zapisywanie stanu do localStorage przy każdej zmianie
  // ---------------------------
  useEffect(() => {
    localStorage.setItem(`deck-${deck.id}-queue`, JSON.stringify(cardsQueue));
    localStorage.setItem(`deck-${deck.id}-ratings`, JSON.stringify(localRatings));
    localStorage.setItem(`deck-${deck.id}-seenCount`, JSON.stringify(cardSeenCount));
  }, [deck.id, cardsQueue, localRatings, cardSeenCount]);

  // ---------------------------
  // 3. Gdy user ogląda nową kartę, zwiększamy jej "seenCount"
  // ---------------------------
  useEffect(() => {
    if (cardsQueue.length === 0) return;
    const cardId = cardsQueue[currentIndex].id;
    setCardSeenCount((prev) => ({
      ...prev,
      [cardId]: (prev[cardId] || 0) + 1,
    }));
  }, [currentIndex, cardsQueue]);

  // ---------------------------
  // 4. Zmiana oceny karty: hard/good -> recycle, easy -> remove
  // ---------------------------
  const handleRating = (rating: number) => {
    if (cardsQueue.length === 0) return;
    const currentCard = cardsQueue[currentIndex];

    // Dodaj ocenę do localRatings
    setLocalRatings((prev) => [
      ...prev,
      {
        flashcardId: currentCard.id,
        rating,
        answeredAt: new Date().toISOString(),
      },
    ]);

    // Kopia kolejki
    const updatedQueue = [...cardsQueue];

    if (rating === 0 || rating === 3) {
      // Hard / Good => przenosimy kartę na koniec
      const cardToRecycle = updatedQueue[currentIndex];
      updatedQueue.splice(currentIndex, 1);
      updatedQueue.push(cardToRecycle);
    } else if (rating === 5) {
      // Easy => usuwamy kartę
      updatedQueue.splice(currentIndex, 1);
    }

    // Jeśli kolejka pusta => koniec
    if (updatedQueue.length === 0) {
      setCardsQueue([]);
      setCurrentIndex(0);
      return;
    }

    // Oblicz next index
    let nextIndex = currentIndex;
    if (nextIndex >= updatedQueue.length) {
      nextIndex = updatedQueue.length - 1;
    }

    setCardsQueue(updatedQueue);
    setCurrentIndex(nextIndex);
    setIsFlipped(false);
  };

  // ---------------------------
  // 5. Zakończenie nauki => hurtowe wysłanie oceny
  // ---------------------------
  const handleFinish = async () => {
    if (localRatings.length === 0) {
      // Nic nie oceniono => wyjdź
      localStorage.removeItem(`deck-${deck.id}-queue`);
      localStorage.removeItem(`deck-${deck.id}-ratings`);
      localStorage.removeItem(`deck-${deck.id}-seenCount`);
      onExit();
      return;
    }
    try {
      setIsSubmitting(true);
      setSubmitError(null);

      // Wysyłamy do backendu (możesz nazwać endpoint inaczej)
      await fetchJson(`${API_BASE_URL}/study_sessions/bulk_record`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          deck_id: deck.id,
          ratings: localRatings,
        }),
      });

      // Po sukcesie czyścimy localStorage + wychodzimy
      localStorage.removeItem(`deck-${deck.id}-queue`);
      localStorage.removeItem(`deck-${deck.id}-ratings`);
      localStorage.removeItem(`deck-${deck.id}-seenCount`);

      onExit();
    } catch (error) {
      if (error instanceof Error) {
        console.error('Błąd przy zapisie fiszek:', error.message);
        setSubmitError(error.message);
      } else {
        console.error('Nieznany błąd:', error);
        setSubmitError('Nieznany błąd podczas zapisywania fiszek.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---------------------------
  // Funkcja flipping
  // ---------------------------
  const handleFlip = () => setIsFlipped(!isFlipped);

  // ---------------------------
  // Jeśli brak kart => user skończył
  // ---------------------------
  if (cardsQueue.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-background p-4">
        <div className="flex flex-col items-center space-y-4">
          <h2 className="text-2xl font-bold">{t('congratulations')}</h2>
          <p>{t('completed_flashcards')}</p>
          {/* Można tu pokazać ile ocen "hard/good/easy" user dał w trakcie sesji */}
          <div className="flex space-x-4">
            <Button onClick={handleFinish} disabled={isSubmitting}>
              {t('save_and_exit')}
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

  // ---------------------------
  // 6. Mamy karty w kolejce => wyświetlamy obecną
  // ---------------------------
  const currentCard = cardsQueue[currentIndex];

  // UI/UX: obliczmy postęp (ile kart oznaczono jako easy)
  const totalCards = deck.flashcards.length;
  const answeredEasyCount = localRatings.filter(r => r.rating === 5).length;
  const progressPercent = Math.round((answeredEasyCount / totalCards) * 100);

  // Ile razy user widział tę kartę?
  const seenCount = cardSeenCount[currentCard.id] || 0;

  return (
    <div className="h-screen w-full bg-background flex items-center justify-center relative">
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
          <Button
            variant="secondary"
            onClick={() => setIsChatOpen(!isChatOpen)}
            className="flex items-center space-x-2"
          >
            <MessageCircle className="h-5 w-5" />
            <span>{isChatOpen ? t('hide_chat') : t('show_chat')}</span>
          </Button>
        </div>

        <div className="flex-grow flex flex-col items-center justify-center p-4 space-y-4">
          {/* Pasek postępu i statystyki */}
          <div className="w-full mb-2">
            <div className="text-sm text-muted-foreground">
              {t('progress')}: {answeredEasyCount}/{totalCards} ({progressPercent}%)
            </div>
            <div className="h-2 w-full bg-muted rounded-md overflow-hidden">
              <div
                className="h-2 bg-primary transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          <div className="mb-4 text-sm font-medium text-primary">
            {t('flashcard_counter', {
              current: currentIndex + 1,
              total: cardsQueue.length
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
                <div className="max-h-full w-full overflow-y-auto scrollbar-thin">
                  <p className="text-xl font-semibold text-center">
                    {currentCard.question}
                  </p>
                  {currentCard.media_url && (
                    <Image
                      src={currentCard.media_url}
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
                <div className="max-h-full w-full overflow-y-auto scrollbar-thin">
                  <p className="text-xl font-semibold text-center">
                    {currentCard.answer}
                  </p>
                  {currentCard.media_url && (
                    <Image
                      src={currentCard.media_url}
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

          {/* Info o ile razy user już widział tę kartę */}
          <div className="text-sm text-muted-foreground">
            {t('seen_this_card_x_times', { count: seenCount })}
          </div>

          {/* Rating Buttons */}
          <div className="h-20 flex justify-center items-center">
            {isFlipped && (
              <div className="flex space-x-4">
                <Button
                  onClick={() => handleRating(0)} // Hard
                  className="bg-red-500 hover:bg-red-600 text-white"
                >
                  {t('hard')}
                </Button>
                <Button
                  onClick={() => handleRating(3)} // Good
                  className="bg-blue-300 hover:bg-blue-400 text-gray-800"
                >
                  {t('good')}
                </Button>
                <Button
                  onClick={() => handleRating(5)} // Easy
                  className="bg-green-500 hover:bg-green-600 text-white"
                >
                  {t('easy')}
                </Button>
              </div>
            )}
          </div>

          {/* Komunikat błędu */}
          {submitError && (
            <p className="text-destructive">{submitError}</p>
          )}

          {/* Przycisk do zapisania i wyjścia */}
          <Button variant="secondary" onClick={handleFinish} disabled={isSubmitting}>
            {t('save_and_exit')}
          </Button>

          {/* Wskaźnik ładowania, gdy wysyłamy oceny */}
          {isSubmitting && (
            <div className="flex items-center space-x-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>{t('saving_results')}</span>
            </div>
          )}
        </div>
      </div>

      {isChatOpen && (
        <div className="w-[40%] h-full fixed right-0 top-0 bg-background border-l border-border z-50">
          <Chat conversationId={conversationId} />
        </div>
      )}
    </div>
  );
}
