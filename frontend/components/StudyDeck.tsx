// components/StudyDeck.tsx

'use client';

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Flashcard {
  id?: number;
  question: string;
  answer: string;
  media_url?: string; // Dodane pole media_url
}

interface Deck {
  id: number;
  name: string;
  description?: string;
  flashcards: Flashcard[];
}

interface StudyDeckProps {
  deck: Deck;
  onExit: () => void;
}

export function StudyDeck({ deck, onExit }: StudyDeckProps) {
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [remainingCards, setRemainingCards] = useState<Flashcard[]>([]);
  const [visibleCard, setVisibleCard] = useState<Flashcard>(deck.flashcards[0] || { question: '', answer: '' });

  const { t } = useTranslation();

  useEffect(() => {
    setRemainingCards([...deck.flashcards]);
  }, [deck]);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    if (!isFlipped) {
      timeoutId = setTimeout(() => {
        setVisibleCard(remainingCards[currentCardIndex] || { question: '', answer: '' });
      }, 250); // Pół czasu trwania animacji flip
    }
    return () => clearTimeout(timeoutId);
  }, [isFlipped, currentCardIndex, remainingCards]);

  const handleFlip = () => {
    setIsFlipped(!isFlipped);
  };

  const handleRating = (rating: 'easy' | 'good' | 'hard') => {
    setIsFlipped(false);

    setTimeout(() => {
      const currentCard = remainingCards[currentCardIndex];
      let updatedRemainingCards = remainingCards.filter((_, index) => index !== currentCardIndex);

      if (rating === 'hard') {
        updatedRemainingCards.splice(Math.min(currentCardIndex + 3, updatedRemainingCards.length), 0, currentCard);
      } else if (rating === 'good') {
        updatedRemainingCards.push(currentCard);
      }

      setRemainingCards(updatedRemainingCards);

      if (updatedRemainingCards.length > 0) {
        setCurrentCardIndex(currentCardIndex % updatedRemainingCards.length);
      } else {
        setCurrentCardIndex(-1);
      }
    }, 250); // Pół czasu trwania animacji flip
  };

  const resetDeck = () => {
    setRemainingCards([...deck.flashcards]);
    setCurrentCardIndex(0);
    setIsFlipped(false);
  };

  if (remainingCards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <h2 className="text-2xl font-bold mb-4">{t('congratulations')}</h2>
        <p className="mb-4">{t('completed_flashcards')}</p>
        <div className="flex space-x-4">
          <Button onClick={resetDeck}>
            <RotateCcw className="mr-2 h-4 w-4" />
            {t('reset_deck')}
          </Button>
          <Button onClick={onExit} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('back_to_decks')}
          </Button>
        </div>
      </div>
    );
  }

  if (currentCardIndex === -1) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <h2 className="text-2xl font-bold mb-4">{t('congratulations')}</h2>
        <p className="mb-4">{t('completed_flashcards')}</p>
        <div className="flex space-x-4">
          <Button onClick={resetDeck}>
            <RotateCcw className="mr-2 h-4 w-4" />
            {t('reset_deck')}
          </Button>
          <Button onClick={onExit} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('back_to_decks')}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="p-4 flex justify-start">
        <Button onClick={onExit} variant="ghost">
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t('exit_study')}
        </Button>
      </header>

      {/* Main Content */}
      <main className="flex-grow flex flex-col items-center justify-center p-4 space-y-4">
        <div className="mb-4 text-sm font-medium">
          {t('card_counter', { current: currentCardIndex + 1, total: remainingCards.length })}
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
                <p className="text-xl font-semibold text-center">{visibleCard?.question}</p>
                {visibleCard?.media_url && (
                  <img
                    src={visibleCard.media_url}
                    alt="Flashcard Media"
                    className="mt-4 max-w-full h-auto rounded shadow"
                  />
                )}
              </div>
            </CardContent>

            {/* Back Side */}
            <CardContent className="absolute w-full h-full p-4 [backface-visibility:hidden] [transform:rotateY(180deg)] flex items-center justify-center">
              <div className="max-h-full w-full overflow-y-auto scrollbar-thin scrollbar-thumb-rounded scrollbar-track-transparent">
                <p className="text-xl font-semibold text-center">{visibleCard?.answer}</p>
                {visibleCard?.media_url && (
                  <img
                    src={visibleCard.media_url}
                    alt="Flashcard Media"
                    className="mt-4 max-w-full h-auto rounded shadow"
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
              <Button onClick={() => handleRating('hard')} className="bg-red-500 hover:bg-red-600 text-white">
                {t('hard')}
              </Button>
              <Button onClick={() => handleRating('good')} className="bg-blue-300 hover:bg-blue-400 text-gray-800">
                {t('good')}
              </Button>
              <Button onClick={() => handleRating('easy')} className="bg-green-500 hover:bg-green-600 text-white">
                {t('easy')}
              </Button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
