'use client';

import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { ArrowLeft, MessageCircle, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import Chat from '@/components/Chat';
import Image from 'next/image';
import { Flashcard, Deck } from '@/types';
import { fetchJson } from '@/utils/fetchJson';
import { cn } from "@/lib/utils";

// Simplified Card component for 3D flip compatibility
const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative rounded-lg border bg-card text-card-foreground",
      "shadow-md",
      "border-border/50",
      "transition-transform duration-700 ease-out",
      className,
    )}
    {...props}
  />
));
Card.displayName = "Card";

// Simplified CardContent for minimal interference
const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "p-4",
        "text-card-foreground",
        className,
      )}
      {...props}
    />
  ),
);
CardContent.displayName = "CardContent";

type LocalRating = {
  flashcard_id: number;
  rating: number;
  answered_at: string;
};

type CardSeenCount = { [flashcardId: number]: number };

interface StudyDeckProps {
  deck: Deck;
  study_session_id: number | null;
  available_cards: Flashcard[];
  next_session_date: string | null;
  conversation_id: number;
  onExit: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';

function shuffle<T>(array: T[]): T[] {
  let currentIndex = array.length;
  while (currentIndex !== 0) {
    const randomIndex = Math.floor(Math.random() * currentIndex);
    currentIndex--;
    [array[currentIndex], array[randomIndex]] = [array[randomIndex], array[currentIndex]];
  }
  return array;
}

export function StudyDeck({
  deck,
  study_session_id,
  available_cards,
  next_session_date,
  conversation_id,
  onExit
}: StudyDeckProps) {
  const { t } = useTranslation();

  // State management
  const shuffledCards = Array.isArray(available_cards) ? shuffle([...available_cards]) : [];
  const [cardsQueue, setCardsQueue] = useState<Flashcard[]>(shuffledCards);
  const [initialTotalCards, setInitialTotalCards] = useState<number>(shuffledCards.length);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [localRatings, setLocalRatings] = useState<LocalRating[]>([]);
  const [cardSeenCount, setCardSeenCount] = useState<CardSeenCount>({});

  // Initialize seen count
  useEffect(() => {
    const initialSeenCount: CardSeenCount = {};
    available_cards.forEach((card) => {
      initialSeenCount[card.id] = 0;
    });
    setCardSeenCount(initialSeenCount);
  }, [available_cards]);

  // Update seen count
  useEffect(() => {
    if (cardsQueue.length === 0) return;
    const cardId = cardsQueue[currentIndex].id;
    setCardSeenCount(prev => ({
      ...prev,
      [cardId]: (prev[cardId] || 0) + 1,
    }));
  }, [currentIndex, cardsQueue]);

  // Save to localStorage
  useEffect(() => {
    if (study_session_id !== null) {
      localStorage.setItem(`session-${study_session_id}-ratings`, JSON.stringify(localRatings));
      localStorage.setItem(`session-${study_session_id}-seenCount`, JSON.stringify(cardSeenCount));
    }
  }, [study_session_id, localRatings, cardSeenCount]);

  // Handle rating
  const handleRating = (rating: number) => {
    if (cardsQueue.length === 0) return;
    const currentCard = cardsQueue[currentIndex];

    setLocalRatings(prev => [
      ...prev,
      {
        flashcard_id: currentCard.id,
        rating,
        answered_at: new Date().toISOString(),
      }
    ]);

    const updatedQueue = [...cardsQueue];
    if (rating === 0 || rating == 3) {
      const [removed] = updatedQueue.splice(currentIndex, 1);
      updatedQueue.push(removed);
    } else if (rating === 5) {
      updatedQueue.splice(currentIndex, 1);
    }

    if (updatedQueue.length === 0) {
      setCardsQueue([]);
      setCurrentIndex(0);
      return;
    }

    let nextIndex = currentIndex;
    if (nextIndex >= updatedQueue.length) {
      nextIndex = updatedQueue.length - 1;
    }
    setCardsQueue(updatedQueue);
    setCurrentIndex(nextIndex);
    setIsFlipped(false);
  };

  // Handle finish
  const handleFinish = async () => {
    if (localRatings.length === 0) {
      clearLocalStorage();
      onExit();
      return;
    }
    try {
      setIsSubmitting(true);
      setSubmitError(null);

      if (study_session_id !== null) {
        const response = await fetchJson(`${API_BASE_URL}/study_sessions/bulk_record`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            session_id: study_session_id,
            deck_id: deck.id,
            ratings: localRatings,
          }),
        });
        console.log('Bulk record response:', response);
      }
      clearLocalStorage();
      onExit();
    } catch (error) {
      if (error instanceof Error) {
        setSubmitError(error.message);
      } else {
        setSubmitError('Unknown error while saving flashcards.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const clearLocalStorage = () => {
    if (study_session_id !== null) {
      localStorage.removeItem(`session-${study_session_id}-ratings`);
      localStorage.removeItem(`session-${study_session_id}-seenCount`);
    }
  };

  // Handle flip
  const handleFlip = () => {
    setIsFlipped(!isFlipped);
  };

  // Handle retake hard cards
  const handleRetakeHardCards = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/study_sessions/retake_hard_cards?deck_id=${deck.id}`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to retake hard cards.');
      }

      const hardCards: Flashcard[] = await response.json();
      if (hardCards.length === 0) {
        alert(t('no_hard_cards_found'));
        return;
      }

      const newShuffled = shuffle([...hardCards]);
      setCardsQueue(newShuffled);
      setCurrentIndex(0);
      setLocalRatings([]);
      const initialSeenCount: CardSeenCount = {};
      hardCards.forEach((card) => {
        initialSeenCount[card.id] = 0;
      });
      setCardSeenCount(initialSeenCount);
      setInitialTotalCards(hardCards.length);
      setIsFlipped(false);
      clearLocalStorage();
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(`${t('error_retake_hard_cards')}: ${err.message}`);
      } else {
        alert(t('error_unexpected_retake_hard_cards'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Handle retake session
  const handleRetakeSession = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/study_sessions/retake_session?deck_id=${deck.id}`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to retake session.');
      }

      const retakeCards: Flashcard[] = await response.json();
      if (retakeCards.length === 0) {
        alert(t('no_cards_to_retake'));
        return;
      }

      const newShuffled = shuffle([...retakeCards]);
      setCardsQueue(newShuffled);
      setCurrentIndex(0);
      setLocalRatings([]);
      const initialSeenCount: CardSeenCount = {};
      retakeCards.forEach((card) => {
        initialSeenCount[card.id] = 0;
      });
      setCardSeenCount(initialSeenCount);
      setInitialTotalCards(retakeCards.length);
      setIsFlipped(false);
      clearLocalStorage();
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(`${t('error_retake_cards')}: ${err.message}`);
      } else {
        alert(t('error_unexpected_retake_cards'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Progress calculation
  const answeredCount = localRatings.filter(r => r.rating === 5).length;
  const progressPercent = initialTotalCards > 0 ? Math.round((answeredCount / initialTotalCards) * 100) : 0;
  const seenCount = cardSeenCount[cardsQueue[currentIndex]?.id] || 0;

  // Completion screen
  if (cardsQueue.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-background p-4">
        <div className="flex flex-col items-center space-y-4">
          <h2 className="text-2xl font-bold">{t('congratulations')}</h2>
          <p className="text-center">{t('completed_flashcards_today')}</p>
          {next_session_date ? (
            <p className="text-center">
              {t('next_session_scheduled', { date: new Date(next_session_date).toLocaleString() })}
            </p>
          ) : (
            <p className="text-center">{t('no_future_session_date_found')}</p>
          )}
          <div>
            <Button
              variant="outline"
              onClick={handleRetakeSession}
              className="mb-2 w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('retake_session')}
                </>
              ) : (
                t('retake_session')
              )}
            </Button>
            <Button
              variant="outline"
              onClick={handleRetakeHardCards}
              className="mb-4 w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('retake_hard_cards')}
                </>
              ) : (
                t('retake_hard_cards')
              )}
            </Button>
            <div className="flex space-x-4">
              {initialTotalCards > 0 && (
                <Button
                  onClick={handleFinish}
                  disabled={isSubmitting || isLoading}
                  className="w-full"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {t('save_and_exit')}
                    </>
                  ) : (
                    t('save_and_exit')
                  )}
                </Button>
              )}
              <Button
                onClick={onExit}
                variant="outline"
                disabled={isLoading}
                className="w-full"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                {t('back_to_decks')}
              </Button>
            </div>
            {(isSubmitting || isLoading) && (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span>{t('loading')}</span>
              </div>
            )}
            {submitError && (
              <p className="text-destructive">{submitError}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full bg-background flex items-center justify-center relative">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-10">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <span className="ml-2 text-white">{t('loading')}</span>
        </div>
      )}
      <div
        className={`transition-all duration-300 ${isChatOpen ? 'mr-[40rem]' : ''} w-full max-w-md flex flex-col min-h-[80vh] bg-card shadow-md rounded-lg`}
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
          {/* Progress bar */}
          <div className="w-full mb-2">
            <div className="text-sm text-muted-foreground">
              {t('progress')}: {answeredCount}/{initialTotalCards} ({progressPercent}%)
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
              current: answeredCount,
              total: initialTotalCards
            })}
          </div>

          {/* Flashcard Area */}
          <div className="w-80 h-64 [perspective:1000px]">
            <Card
              className={`w-full h-full cursor-pointer [transform-style:preserve-3d] rounded-lg ${isFlipped ? '[transform:rotateY(180deg)]' : ''}`}
              onClick={handleFlip}
            >
              {/* Front Side */}
              <CardContent className="absolute w-full h-full p-4 bg-card [backface-visibility:hidden] flex items-center justify-center">
                <div className="max-h-full w-full overflow-y-auto scrollbar-thin text-center">
                  <p className="text-xl font-semibold text-card-foreground">
                    {cardsQueue[currentIndex].question}
                  </p>
                  {cardsQueue[currentIndex].media_url && (
                    <Image
                      src={cardsQueue[currentIndex].media_url}
                      alt="Flashcard Media"
                      className="mt-4 max-w-full h-auto rounded shadow"
                      width={500}
                      height={300}
                      style={{ objectFit: 'contain' }}
                    />
                  )}
                  <p className="text-sm text-muted-foreground italic mt-2">
                    {t('click_to_flip')}
                  </p>
                </div>
              </CardContent>

              {/* Back Side */}
              <CardContent className="absolute w-full h-full p-4 bg-card [backface-visibility:hidden] [transform:rotateY(180deg)] flex items-center justify-center">
                <div className="max-h-full w-full overflow-y-auto scrollbar-thin text-center">
                  <p className="text-xl font-semibold text-card-foreground">
                    {cardsQueue[currentIndex].answer}
                  </p>
                  {cardsQueue[currentIndex].media_url && (
                    <Image
                      src={cardsQueue[currentIndex].media_url}
                      alt="Flashcard Media"
                      className="mt-4 max-w-full h-auto rounded shadow"
                      width={500}
                      height={300}
                      style={{ objectFit: 'contain' }}
                    />
                  )}
                  <p className="text-sm text-muted-foreground italic mt-2">
                    {t('click_to_flip')}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="text-sm text-muted-foreground">
            {t('seen_this_card_x_times', { count: seenCount })}
            {cardsQueue[currentIndex].repetitions !== undefined && (
              <span className="ml-2">
                {t('repetition_count')}: {cardsQueue[currentIndex].repetitions}
              </span>
            )}
          </div>

          {/* Rating buttons */}
          <div className="h-20 flex justify-center items-center">
            {isFlipped && (
              <div className="flex space-x-4">
                <Button
                  onClick={() => handleRating(0)}
                  className="bg-red-500 hover:bg-red-600 text-white"
                >
                  {t('hard')}
                </Button>
                <Button
                  onClick={() => handleRating(3)}
                  className="bg-blue-300 hover:bg-blue-400 text-gray-800"
                >
                  {t('good')}
                </Button>
                <Button
                  onClick={() => handleRating(5)}
                  className="bg-green-500 hover:bg-green-600 text-white"
                >
                  {t('easy')}
                </Button>
              </div>
            )}
          </div>

          {submitError && (
            <p className="text-destructive">{submitError}</p>
          )}

          <Button variant="secondary" onClick={handleFinish} disabled={isSubmitting || isLoading}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('save_and_exit')}
              </>
            ) : (
              t('save_and_exit')
            )}
          </Button>

          {(isSubmitting || isLoading) && (
            <div className="flex items-center space-x-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>{t('saving_results')}</span>
            </div>
          )}
        </div>
      </div>

      {/* Chat container */}
      {isChatOpen && (
        <div
          className="fixed top-0 left-0 w-full h-full md:w-[40%] md:right-0 md:left-auto bg-background md:border-l border-border z-50"
        >
          <div className="absolute top-4 left-4 md:hidden">
            <Button variant="ghost" onClick={() => setIsChatOpen(false)}>
              <ArrowLeft className="h-6 w-6" />
            </Button>
          </div>
          <Chat conversationId={conversation_id} />
        </div>
      )}
    </div>
  );
}