'use client';

import React, { useState, useEffect, useCallback, MouseEvent } from 'react';
import { EditDeckDialog } from '@/components/EditDeckDialog';
import { ImportFlashcardsModal } from '@/components/ImportFlashcardsModal';
import { Button } from "@/components/ui/button";
import { PlusCircle, BookOpen, Loader2, Info, ChevronRight, MoreVertical, Edit2, Trash2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { StudyDeck } from '@/components/StudyDeck';
import { CustomTooltip } from '@/components/CustomTooltip';
import { useTranslation } from 'react-i18next';

import { Deck, Flashcard, ErrorResponse } from '@/types';

export default function FlashcardsPage() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [studyingDeck, setStudyingDeck] = useState<{
    deck: Deck;
    study_session_id: number | null;
    available_cards: Flashcard[];
    next_session_date: string | null;
    conversation_id: number;
  } | null>(null);

  const [openCollapsibles, setOpenCollapsibles] = useState<{ [key: number]: boolean }>({});

  const { t } = useTranslation();

  const API_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';
  const API_BASE_URL = `${API_URL}/decks/`;
  const STUDY_SESSIONS_URL = `${API_URL}/study_sessions/`;

  /**
   * Pobiera decki.
   */
  const fetchDecks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(API_BASE_URL, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        const errorData: ErrorResponse = await response.json();
        throw new Error(errorData.detail as string || 'Nie udało się pobrać decków.');
      }
      const data: Deck[] = await response.json();
      setDecks(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || t('error_fetch_decks'));
      } else {
        setError(t('error_unexpected_fetch_decks'));
      }
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [API_BASE_URL, t]);

  useEffect(() => {
    fetchDecks();
  }, [fetchDecks]);

  /**
   * Funkcja asynchroniczna zapisywania decka.
   */
  const handleSave = async (updatedDeck: Deck): Promise<void> => {
    try {
      const bodyData = {
        name: updatedDeck.name,
        description: updatedDeck.description,
        flashcards: updatedDeck.flashcards.map(fc => ({
          question: fc.question,
          answer: fc.answer,
          media_url: fc.media_url,
        })),
        conversation_id: updatedDeck.conversation_id,
      };

      if (updatedDeck.id === 0) {
        // Tworzenie nowego decka – domyślnie conversation_id = 0
        const response = await fetch(API_BASE_URL, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(bodyData),
        });
        if (!response.ok) {
          const errorData: ErrorResponse = await response.json();
          throw new Error(errorData.detail as string || 'Nie udało się stworzyć decka.');
        }
        const newDeck: Deck = await response.json();
        setDecks(prevDecks => [...prevDecks, newDeck]);
      } else {
        // Aktualizacja istniejącego decka
        const response = await fetch(`${API_BASE_URL}${updatedDeck.id}/`, {
          method: 'PUT',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(bodyData),
        });
        if (!response.ok) {
          const errorData: ErrorResponse = await response.json();
          throw new Error(errorData.detail as string || 'Nie udało się zaktualizować decka.');
        }
        const updatedDeckFromServer: Deck = await response.json();
        setDecks(prevDecks =>
          prevDecks.map(deck =>
            deck.id === updatedDeckFromServer.id ? updatedDeckFromServer : deck
          )
        );
      }
      // Zamknięcie Collapsible po zapisaniu
      setOpenCollapsibles(prev => ({ ...prev, [updatedDeck.id]: false }));
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t('error_saving_deck')}: ${err.message}`);
      } else {
        setError(t('error_unexpected_saving_deck'));
      }
      console.error('Error saving deck:', err);
    }
  };

  // Wrapper do onSave – zwraca void.
  const handleSaveWrapper = (updatedDeck: Deck): void => {
    void handleSave(updatedDeck);
  };

  const handleDelete = async (deckId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}${deckId}/`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!response.ok) {
        const errorData: ErrorResponse = await response.json();
        throw new Error(errorData.detail as string || 'Nie udało się usunąć decka.');
      }
      setDecks(prev => prev.filter(deck => deck.id !== deckId));
      setOpenCollapsibles(prev => ({ ...prev, [deckId]: false }));
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t('error_deleting_deck')}: ${err.message}`);
      } else {
        setError(t('error_unexpected_deleting_deck'));
      }
      console.error('Error deleting deck:', err);
    }
  };

  /**
   * Rozpoczyna naukę danej talii.
   * Jeśli talia nie ma ustawionego conversation_id (lub ma 0), tworzymy nową konwersację,
   * aktualizujemy decka w bazie oraz stan lokalny, aby zapisać nowy conversation_id.
   */
  const handleStudy = async (deck: Deck) => {
    try {
      let convId = deck.conversation_id;
      if (!convId || convId === 0) {
        // Tworzymy nową konwersację dla tego decka
        const convResponse = await fetch(`${API_URL}/chats/`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ deck_id: deck.id, title: deck.name })
        });
        if (!convResponse.ok) {
          const convError = await convResponse.json();
          throw new Error(convError.detail || 'Nie udało się utworzyć konwersacji.');
        }
        const newConv = await convResponse.json();
        convId = newConv.id;
        console.log(convId)
        // Aktualizujemy decka w bazie, zapisując nowe conversation_id
        const updateResponse = await fetch(`${API_BASE_URL}${deck.id}/`, {
          method: 'PUT',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: deck.name,
            description: deck.description,
            flashcards: deck.flashcards.map(fc => ({
              id: fc.id,
              question: fc.question,
              answer: fc.answer,
              media_url: fc.media_url,
            })),
            conversation_id: convId,
          }),
        });
        if (!updateResponse.ok) {
          const updateError = await updateResponse.json();
          throw new Error(updateError.detail || 'Nie udało się zaktualizować decka.');
        }
        const updatedDeck = await updateResponse.json();
        setDecks(prev => prev.map(d => d.id === deck.id ? updatedDeck : d));
        deck = updatedDeck;
      }

      // Rozpoczynamy sesję nauki wykorzystując conversation_id zapisane w decku
      const response = await fetch(`${STUDY_SESSIONS_URL}start`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deck_id: deck.id, conversation_id: convId })
      });
      if (!response.ok) {
        const errorData: ErrorResponse = await response.json();
        let errorMessage = 'Nie udało się rozpocząć sesji nauki.';
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((err) =>
            (typeof err === 'object' && 'msg' in err ? err.msg : String(err))
          ).join(', ');
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        }
        throw new Error(errorMessage);
      }
      const data = await response.json();
      const { study_session_id, available_cards, next_session_date } = data;
      if (!Array.isArray(available_cards)) {
        throw new Error('Invalid response format: available_cards is not an array.');
      }
      setStudyingDeck({
        deck,
        study_session_id,
        available_cards,
        next_session_date,
        conversation_id: convId,
      });
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t('error_starting_study')}: ${err.message}`);
      } else {
        setError(t('error_unexpected_starting_study'));
      }
      console.error('Error starting study session:', err);
    }
  };

  const handleExitStudy = () => {
    setStudyingDeck(null);
  };

  const toggleCollapsibles = (deckId: number) => {
    setOpenCollapsibles(prev => ({
      ...prev,
      [deckId]: !prev[deckId]
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="mr-2 h-16 w-16 animate-spin" />
        <span className="text-xl font-semibold">{t('loading_decks')}</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle className="text-destructive">{t('error')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchDecks}>{t('try_again')}</Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (studyingDeck) {
    return (
      <StudyDeck
        deck={studyingDeck.deck}
        study_session_id={studyingDeck.study_session_id}
        available_cards={studyingDeck.available_cards}
        next_session_date={studyingDeck.next_session_date}
        conversation_id={studyingDeck.conversation_id}
        onExit={handleExitStudy}
      />
    );
  }

  return (
    <div className="p-4 max-w-full mx-auto">
      {/* Header */}
      <div className="text-center mb-6 flex flex-col items-center justify-center space-y-2">
        <h1 className="text-5xl font-extrabold text-primary">{t('flashcards')}</h1>
        <div className="flex items-center space-x-2">
          <CustomTooltip content={t('flashcards_tooltip')}>
            <Button variant="ghost" size="icon">
              <Info className="h-6 w-6" />
              <span className="sr-only">{t('more_information')}</span>
            </Button>
          </CustomTooltip>
        </div>
      </div>

      {decks.length === 0 ? (
        <div className="flex flex-col items-center justify-center">
          <Card className="w-full max-w-2xl shadow-lg">
            <CardHeader>
              <CardTitle className="text-3xl font-bold">{t('welcome_flashcards')}</CardTitle>
              <CardDescription className="text-xl">{t('get_started_create_deck')}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center space-y-6 py-12">
              <BookOpen className="h-40 w-40 text-muted-foreground" />
              <p className="text-center text-muted-foreground text-xl">
                {t('no_flashcard_decks')}
              </p>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4">
              <ImportFlashcardsModal
                trigger={
                  <Button className="flex items-center space-x-2 px-6 py-3">
                    <span>{t('import_flashcards')}</span>
                  </Button>
                }
                onImportSuccess={fetchDecks}
              />
              <EditDeckDialog
                deck={{ id: 0, name: '', description: '', flashcards: [], conversation_id: 0 }}
                onSave={handleSaveWrapper}
                trigger={
                  <Button className="flex items-center space-x-2 px-6 py-3 bg-primary hover:bg-primary-dark text-primary-foreground">
                    <PlusCircle className="h-6 w-6" />
                    <span>{t('create_your_first_deck')}</span>
                  </Button>
                }
              />
            </CardFooter>
          </Card>
        </div>
      ) : (
        <>
          {/* Buttons for Import and Create New Deck */}
          <div className="mb-8 flex flex-col md:flex-row justify-center md:justify-end space-y-4 md:space-y-0 md:space-x-4 px-4">
            <ImportFlashcardsModal
              trigger={
                <Button className="flex items-center space-x-2 px-4 py-2 md:px-6 md:py-3 w-full md:w-auto">
                  <span>{t('import_flashcards')}</span>
                </Button>
              }
              onImportSuccess={fetchDecks}
            />
            <EditDeckDialog
              deck={{ id: 0, name: '', description: '', flashcards: [], conversation_id: 0 }}
              onSave={handleSaveWrapper}
              trigger={
                <Button className="flex items-center space-x-2 px-4 py-2 md:px-6 md:py-3 bg-primary hover:bg-primary-dark text-primary-foreground w-full md:w-auto">
                  <PlusCircle className="h-5 w-5 md:h-6 md:w-6" />
                  <span>{t('create_new_deck')}</span>
                </Button>
              }
            />
          </div>
          {/* Decks grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {decks.map(deck => (
              <Card key={deck.id} className="flex flex-col min-h-[350px] shadow-lg relative">
                <CardHeader className="flex flex-col">
                  <div className="flex justify-between items-center space-x-4">
                    <CardTitle className="text-2xl font-bold truncate">{deck.name}</CardTitle>
                    <Collapsible open={openCollapsibles[deck.id] || false} onOpenChange={() => toggleCollapsibles(deck.id)}>
                      <CollapsibleTrigger asChild>
                        <Button variant="ghost" size="sm" className="p-1 text-secondary hover:text-primary" aria-label="Opcje">
                          <MoreVertical className="h-5 w-5 text-primary" />
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="absolute right-4 top-16 bg-card border border-border rounded-md shadow-lg z-50 p-2">
                        <div className="flex flex-col">
                          <EditDeckDialog
                            deck={deck}
                            onSave={handleSaveWrapper}
                            trigger={
                              <Button variant="ghost" size="sm" className="flex items-center justify-start w-full px-4 py-2 hover:bg-secondary/80 text-primary">
                                <Edit2 className="h-4 w-4 mr-2" />
                                {t('edit')}
                              </Button>
                            }
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            className="flex items-center justify-start w-full px-4 py-2 text-destructive hover:bg-secondary/80"
                            onClick={(e: MouseEvent<HTMLButtonElement>) => {
                              e.stopPropagation();
                              handleDelete(deck.id);
                            }}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            {t('delete')}
                          </Button>
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  </div>
                  <CardDescription className="mt-3 text-lg break-words">
                    {deck.description || t('no_description')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow">
                  <p className="text-lg text-muted-foreground">
                    {deck.flashcards.length} {t('flashcards_lowercase')}
                  </p>
                </CardContent>
                <CardFooter className="mt-auto flex justify-end space-x-2">
                  <Button variant="ghost" size="sm" onClick={() => handleStudy(deck)} className="flex items-center space-x-2 px-4 py-2">
                    <span>{t('study')}</span>
                    <ChevronRight className="h-5 w-5" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
