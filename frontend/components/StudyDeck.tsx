'use client';

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, RotateCcw, XCircle, MessageCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import Chat from '@/components/Chat'; // <--- importujemy chat

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

  // Stan do sterowania chatem
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Przykładowe userId i conversationId do czatu (możesz dopasować do logiki)
  const userId = 'user-123';
  const conversationId = deck.id;
  // Możesz też użyć np. deck.id + 1000 czy innej konwencji, by każda talia miała osobny conversationId.

  const { t } = useTranslation();

  useEffect(() => {
    setRemainingCards([...deck.flashcards]);
  }, [deck]);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    if (!isFlipped) {
      timeoutId = setTimeout(() => {
        setVisibleCard(remainingCards[currentCardIndex] || { question: '', answer: '' });
      }, 250); // połowa czasu animacji flip
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
      const updatedRemainingCards = remainingCards.filter((_, index) => index !== currentCardIndex);

      if (rating === 'hard') {
        // Wkładamy kartę 3 miejsca dalej
        updatedRemainingCards.splice(
          Math.min(currentCardIndex + 3, updatedRemainingCards.length),
          0,
          currentCard
        );
      } else if (rating === 'good') {
        // Wkładamy kartę na koniec
        updatedRemainingCards.push(currentCard);
      }
      // 'easy' -> karta znika (nie wraca do talii)

      setRemainingCards(updatedRemainingCards);

      if (updatedRemainingCards.length > 0) {
        setCurrentCardIndex(currentCardIndex % updatedRemainingCards.length);
      } else {
        setCurrentCardIndex(-1);
      }
    }, 250);
  };

  const resetDeck = () => {
    setRemainingCards([...deck.flashcards]);
    setCurrentCardIndex(0);
    setIsFlipped(false);
  };

  if (remainingCards.length === 0 || currentCardIndex === -1) {
    return (
      <div className="h-screen flex items-center justify-center bg-background p-4">
        <div className="flex flex-col items-center justify-center space-y-4">
          <h2 className="text-2xl font-bold">{t('congratulations')}</h2>
          <p>{t('completed_flashcards')}</p>
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
            {t('card_counter', {
              current: currentCardIndex + 1,
              total: remainingCards.length
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
                <Button
                  onClick={() => handleRating('hard')}
                  className="bg-red-500 hover:bg-red-600 text-white"
                >
                  {t('hard')}
                </Button>
                <Button
                  onClick={() => handleRating('good')}
                  className="bg-blue-300 hover:bg-blue-400 text-gray-800"
                >
                  {t('good')}
                </Button>
                <Button
                  onClick={() => handleRating('easy')}
                  className="bg-green-500 hover:bg-green-600 text-white"
                >
                  {t('easy')}
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Panel czatu z prawej strony */}
      {isChatOpen && (
        <div className="w-[40rem] h-full fixed right-0 top-0 bg-background border-l border-border z-50">
          <Chat userId={userId} conversationId={conversationId} />
        </div>
      )}
    </div>
  );
}
