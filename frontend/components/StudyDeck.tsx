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

type LocalRating = {
  flashcard_id: number;
  rating: number;
  answered_at: string;
};

type CardSeenCount = { [flashcardId: number]: number };

interface StudyDeckProps {
  deck: Deck;
  study_session_id: number;
  available_cards: Flashcard[];
  onExit: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8000/api';

export function StudyDeck({ deck, study_session_id, available_cards, onExit }: StudyDeckProps) {
  const { t } = useTranslation();

  // Queue of flashcards
  const [cardsQueue, setCardsQueue] = useState<Flashcard[]>(Array.isArray(available_cards) ? available_cards : []);
  const [currentIndex, setCurrentIndex] = useState(0);
  // Rated flashcards
  const [localRatings, setLocalRatings] = useState<LocalRating[]>([]);
  // How many times user has seen a card
  const [cardSeenCount, setCardSeenCount] = useState<CardSeenCount>({});

  // State for card flipping
  const [isFlipped, setIsFlipped] = useState(false);
  // Chat
  const [isChatOpen, setIsChatOpen] = useState(false);
  // State for submission
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Date for next session
  const [nextSessionDate, setNextSessionDate] = useState<string | null>(null);

  // ConversationId for Chat
  const conversationId = deck.id;

  // Initialize seen count from available_cards
  useEffect(() => {
    const initialSeenCount: CardSeenCount = {};
    if (Array.isArray(available_cards)) {
      available_cards.forEach(card => {
        initialSeenCount[card.id] = 0;
      });
    }
    setCardSeenCount(initialSeenCount);
  }, [available_cards]);

  // Update seen count when currentIndex changes
  useEffect(() => {
    if (cardsQueue.length === 0) return;
    const cardId = cardsQueue[currentIndex].id;
    setCardSeenCount(prev => ({
      ...prev,
      [cardId]: (prev[cardId] || 0) + 1,
    }));
  }, [currentIndex, cardsQueue]);

  // Save state to localStorage
  useEffect(() => {
    localStorage.setItem(`session-${study_session_id}-ratings`, JSON.stringify(localRatings));
    localStorage.setItem(`session-${study_session_id}-seenCount`, JSON.stringify(cardSeenCount));
  }, [study_session_id, localRatings, cardSeenCount]);

  // Function to rate a card
  const handleRating = (rating: number) => {
    if (cardsQueue.length === 0) return;
    const currentCard = cardsQueue[currentIndex];

    // Add rating to localRatings
    setLocalRatings(prev => [
      ...prev,
      {
        flashcard_id: currentCard.id,
        rating,
        answered_at: new Date().toISOString(),
      }
    ]);

    const updatedQueue = [...cardsQueue];

    // Hard (0) / Good(3) => recycling
    if (rating === 0 || rating === 3) {
      const [removed] = updatedQueue.splice(currentIndex, 1);
      updatedQueue.push(removed);
    } else if (rating === 5) {
      // Easy => remove
      updatedQueue.splice(currentIndex, 1);
    }

    // If queue is empty
    if (updatedQueue.length === 0) {
      setCardsQueue([]);
      setCurrentIndex(0);
      return;
    }

    // Move to next card
    let nextIndex = currentIndex;
    if (nextIndex >= updatedQueue.length) {
      nextIndex = updatedQueue.length - 1;
    }
    setCardsQueue(updatedQueue);
    setCurrentIndex(nextIndex);
    setIsFlipped(false);
  };

  // Function to submit ratings and finish the session
  const handleFinish = async () => {
    if (localRatings.length === 0) {
      clearLocalStorage();
      onExit();
      return;
    }
    try {
      setIsSubmitting(true);
      setSubmitError(null);

      await fetchJson(`${API_BASE_URL}/study_sessions/bulk_record`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          session_id: study_session_id,
          deck_id: deck.id,
          ratings: localRatings,
        }),
      });

      clearLocalStorage();
      onExit();
    } catch (error) {
      if (error instanceof Error) {
        console.error('Error saving flashcards:', error.message);
        setSubmitError(error.message);
      } else {
        console.error('Unknown error:', error);
        setSubmitError('Unknown error while saving flashcards.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const clearLocalStorage = () => {
    localStorage.removeItem(`session-${study_session_id}-ratings`);
    localStorage.removeItem(`session-${study_session_id}-seenCount`);
  };

  // Function to flip the card
  const handleFlip = () => {
    setIsFlipped(!isFlipped);
  };

  // Fetch next review date after finishing the session
  useEffect(() => {
    if (cardsQueue.length === 0) {
      fetchEarliestNextReview(deck.id);
    }
  }, [cardsQueue.length, deck.id]);

  const fetchEarliestNextReview = async (deckId: number) => {
    try {
      const data = await fetchJson<{ next_review: string | null }>(
        `${API_BASE_URL}/study_sessions/next_review_date?deck_id=${deckId}`,
        { method: 'GET', credentials: 'include' }
      );
      setNextSessionDate(data.next_review);
    } catch (e) {
      console.error('Error fetching nextReviewDate:', e);
      setNextSessionDate(null);
    }
  };

  // Function to retake cards from the session
  const handleRetakeSession = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/study_sessions/session/${study_session_id}/retake_cards`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to retake cards.');
      }

      const retakeCards: Flashcard[] = await response.json();

      if (retakeCards.length === 0) {
        alert(t('no_cards_to_retake'));
        return;
      }

      setCardsQueue(retakeCards);
      setCurrentIndex(0);
      setLocalRatings([]);
      setNextSessionDate(null);
      setIsFlipped(false);
      clearLocalStorage();
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(`${t('error_retake_cards')}: ${err.message}`);
      } else {
        alert(t('error_unexpected_retake_cards'));
      }
      console.error('Error retaking session cards:', err);
    }
  };

  // Function to retake hard cards
  const handleRetakeHardCards = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/study_sessions/retake_hard_cards?deck_id=${deck.id}&max_ef=1.8`, {
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

      setCardsQueue(hardCards);
      setCurrentIndex(0);
      setLocalRatings([]);
      setNextSessionDate(null);
      setIsFlipped(false);
      clearLocalStorage();
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(`${t('error_retake_hard_cards')}: ${err.message}`);
      } else {
        alert(t('error_unexpected_retake_hard_cards'));
      }
      console.error('Error retaking hard cards:', err);
    }
  };

  // When cardsQueue is empty, show completion screen
  if (cardsQueue.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-background p-4">
        <div className="flex flex-col items-center space-y-4">
          <h2 className="text-2xl font-bold">{t('congratulations')}</h2>
          <p className="text-center">{t('completed_flashcards_today')}</p>

          {nextSessionDate ? (
            <p className="text-center">
              {t('next_session_scheduled', { date: new Date(nextSessionDate).toLocaleString() })}
            </p>
          ) : (
            <p className="text-center">{t('no_future_session_date_found')}</p>
          )}

          <Button
            variant="outline"
            onClick={handleRetakeSession}
            className="mb-2"
          >
            {t('retake_session')}
          </Button>

          <Button
            variant="outline"
            onClick={handleRetakeHardCards}
            className="mb-4"
          >
            {t('retake_hard_cards')}
          </Button>

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

  // If have flashcards, show study screen
  const currentCard = cardsQueue[currentIndex];

  const totalCards = deck.flashcards.length;
  const answeredEasyCount = localRatings.filter(r => r.rating === 5).length;
  const progressPercent = totalCards > 0 ? Math.round((answeredEasyCount / totalCards) * 100) : 0;
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
          {/* Progress bar and stats */}
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

          <div className="text-sm text-muted-foreground">
            {t('seen_this_card_x_times', { count: seenCount })}
          </div>

          {/* Rating buttons */}
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

          {/* Possible error */}
          {submitError && (
            <p className="text-destructive">{submitError}</p>
          )}

          {/* Save and exit button */}
          <Button variant="secondary" onClick={handleFinish} disabled={isSubmitting}>
            {t('save_and_exit')}
          </Button>

          {/* Loading indicator when saving */}
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
