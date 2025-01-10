// app/flashcards/page.tsx

'use client';

import React, { useState, useEffect, useCallback, FormEvent, MouseEvent } from 'react';
import * as Dialog from '@radix-ui/react-dialog'; // Poprawny import Radix Dialog
import { EditDeckDialog } from '@/components/EditDeckDialog';
import { Button } from "@/components/ui/button";
import { PlusCircle, BookOpen, Loader2, Info, ChevronRight, MoreVertical, Edit2, Trash2, Upload } from 'lucide-react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'; // Upewnij się, że te komponenty są z Radix lub odpowiedniej biblioteki
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

import { StudyDeck } from '@/components/StudyDeck';
import { CustomTooltip } from '@/components/CustomTooltip';
import { useTranslation } from 'react-i18next';

import { Deck,} from '@/types'; // Import typów z centralnego pliku

export default function FlashcardsPage() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [studyingDeck, setStudyingDeck] = useState<Deck | null>(null);
  const [importing, setImporting] = useState<boolean>(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);
  const [openCollapsibles, setOpenCollapsibles] = useState<{ [key: number]: boolean }>({});

  const { t } = useTranslation();

  const API_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';
  const API_BASE_URL = `${API_URL}/decks/`;
  /**
   * Funkcja do pobierania decków
   */
  const fetchDecks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(API_BASE_URL, {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'Authorization': 'TorchED_AUTH'}
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Nie udało się pobrać decków.');
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
   * Funkcja do zapisywania (tworzenia/aktualizacji) decka
   */
  const handleSave = async (updatedDeck: Deck) => {
    try {
      const bodyData = {
        name: updatedDeck.name,
        description: updatedDeck.description,
        flashcards: updatedDeck.flashcards.map(fc => ({
          question: fc.question,
          answer: fc.answer,
          media_url: fc.media_url,
        })),
      };

      if (updatedDeck.id === 0) {
        // Tworzenie nowego decka
        const response = await fetch(API_BASE_URL, {
          method: 'POST',
          credentials: 'include',
          body: JSON.stringify(bodyData),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Nie udało się stworzyć decka.');
        }

        const newDeck: Deck = await response.json();
        setDecks(prevDecks => [...prevDecks, newDeck]);
      } else {
        // Aktualizacja istniejącego decka
        const response = await fetch(`${API_BASE_URL}${updatedDeck.id}/`, {
          method: 'PUT',
          credentials: 'include',
          body: JSON.stringify({
            name: updatedDeck.name,
            description: updatedDeck.description,
            flashcards: updatedDeck.flashcards.map(fc => ({
              id: fc.id, // id jest teraz wymagane
              question: fc.question,
              answer: fc.answer,
              media_url: fc.media_url,
            })),
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Nie udało się zaktualizować decka.');
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

  /**
   * Funkcja do usuwania decka
   */
  const handleDelete = async (deckId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}${deckId}/`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Nie udało się usunąć decka.');
      }

      setDecks(prev => prev.filter(deck => deck.id !== deckId));

      // Zamknięcie Collapsible po usunięciu
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
   * Funkcja do studiowania decka
   */
  const handleStudy = (deck: Deck) => {
    setStudyingDeck(deck);
  };

  /**
   * Funkcja do wyjścia z trybu nauki
   */
  const handleExitStudy = () => {
    setStudyingDeck(null);
  };

  /**
   * Funkcja do importu fiszek
   */
  const handleImport = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const file = formData.get('file') as File;

    if (!file) {
      setImportError(t('no_file_selected'));
      return;
    }

    setImporting(true);
    setImportError(null);
    setImportSuccess(null);

    try {
      const response = await fetch(`${API_BASE_URL}import/`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Nie udało się zaimportować fiszek.');
      }

      setImportSuccess(t('import_success'));
      fetchDecks();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setImportError(err.message || t('import_failed'));
      } else {
        setImportError(t('import_failed'));
      }
      console.error(err);
    } finally {
      setImporting(false);
    }
  };

  /**
   * Funkcja do togglowania Collapsible dla konkretnego decka
   */
  const toggleCollapsible = (deckId: number) => {
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
    return <StudyDeck deck={studyingDeck} onExit={handleExitStudy} />;
  }

  return (
    <div className="p-4 max-w-full mx-auto">
      {/* Header section */}
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
        // Stan pusty
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
              {/* Dialog Import Flashcards */}
              <Dialog.Root>
                <Dialog.Trigger asChild>
                  <Button className="flex items-center space-x-2 px-6 py-3">
                    <Upload className="h-6 w-6" />
                    <span>{t('import_flashcards')}</span>
                  </Button>
                </Dialog.Trigger>
                <Dialog.Content>
                  {/* Formularz importu */}
                  <form onSubmit={handleImport} className="flex flex-col space-y-4">
                    <DialogHeader className="flex flex-row items-center justify-between">
                      <div>
                        <DialogTitle>{t('import_flashcards')}</DialogTitle>
                        <DialogDescription>
                          {t('select_flashcards_file')}
                        </DialogDescription>
                      </div>
                      <CustomTooltip content="Tutaj wgrywasz fiszki (CSV, APKG lub TXT). Możesz też ustawić nazwę i opis, które pojawią się jako nowa talia.">
                        <Info className="h-6 w-6 text-muted-foreground cursor-pointer" />
                      </CustomTooltip>
                    </DialogHeader>

                    {/* Pola nazwy i opisu talii */}
                    <label className="font-medium">{t('deck_name')}</label>
                    <input
                      type="text"
                      name="deck_name"
                      placeholder={t('optional_deck_name') || 'Opcjonalna nazwa talii'}
                      className="border border-input rounded-md p-2"
                    />
                    <label className="font-medium">{t('deck_description')}</label>
                    <textarea
                      name="deck_description"
                      placeholder={t('optional_deck_description') || 'Opcjonalny opis talii'}
                      className="border border-input rounded-md p-2"
                      rows={3}
                    />

                    <input
                      type="file"
                      name="file"
                      accept=".csv,.apkg,.txt"
                      required
                      className="border border-input rounded-md p-2"
                    />

                    {importError && <p className="text-red-500">{importError}</p>}
                    {importSuccess && <p className="text-green-500">{importSuccess}</p>}

                    <DialogFooter className="flex justify-end space-x-2">
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => {
                          setImportError(null);
                          setImportSuccess(null);
                        }}
                      >
                        {t('cancel')}
                      </Button>
                      <Button type="submit" disabled={importing}>
                        {importing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                        {t('import')}
                      </Button>
                    </DialogFooter>
                  </form>
                </Dialog.Content>
              </Dialog.Root>

              {/* Dialog Create New Deck */}
              <EditDeckDialog
                deck={{ id: 0, name: '', description: '', flashcards: [] }}
                onSave={handleSave}
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
          {/* Sekcja przycisków Import i Create New Deck */}
          <div className="mb-8 flex justify-end space-x-4">
            {/* Dialog Import Flashcards */}
            <Dialog.Root>
              <Dialog.Trigger asChild>
                <Button className="flex items-center space-x-2 px-6 py-3">
                  <Upload className="h-6 w-6" />
                  <span>{t('import_flashcards')}</span>
                </Button>
              </Dialog.Trigger>
              <Dialog.Content>
                {/* Formularz importu */}
                <form onSubmit={handleImport} className="flex flex-col space-y-4">
                  <DialogHeader className="flex flex-row items-center justify-between">
                    <div>
                      <DialogTitle>{t('import_flashcards')}</DialogTitle>
                      <DialogDescription>
                        {t('select_flashcards_file')}
                      </DialogDescription>
                    </div>
                    <CustomTooltip content="Tutaj wgrywasz fiszki (CSV, APKG lub TXT). Możesz też ustawić nazwę i opis, które pojawią się jako nowa talia.">
                      <Info className="h-6 w-6 text-muted-foreground cursor-pointer" />
                    </CustomTooltip>
                  </DialogHeader>

                  {/* Pola nazwy i opisu talii */}
                  <label className="font-medium">{t('deck_name')}</label>
                  <input
                    type="text"
                    name="deck_name"
                    placeholder={t('optional_deck_name') || 'Opcjonalna nazwa talii'}
                    className="border border-input rounded-md p-2"
                  />
                  <label className="font-medium">{t('deck_description')}</label>
                  <textarea
                    name="deck_description"
                    placeholder={t('optional_deck_description') || 'Opcjonalny opis talii'}
                    className="border border-input rounded-md p-2"
                    rows={3}
                  />

                  <input
                    type="file"
                    name="file"
                    accept=".csv,.apkg,.txt"
                    required
                    className="border border-input rounded-md p-2"
                  />

                  {importError && <p className="text-red-500">{importError}</p>}
                  {importSuccess && <p className="text-green-500">{importSuccess}</p>}

                  <DialogFooter className="flex justify-end space-x-2">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => {
                        setImportError(null);
                        setImportSuccess(null);
                      }}
                    >
                      {t('cancel')}
                    </Button>
                    <Button type="submit" disabled={importing}>
                      {importing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      {t('import')}
                    </Button>
                  </DialogFooter>
                </form>
              </Dialog.Content>
            </Dialog.Root>

            {/* Dialog Create New Deck */}
            <EditDeckDialog
              deck={{ id: 0, name: '', description: '', flashcards: [] }}
              onSave={handleSave}
              trigger={
                <Button className="flex items-center space-x-2 px-6 py-3 bg-primary hover:bg-primary-dark text-primary-foreground">
                  <PlusCircle className="h-6 w-6" />
                  <span>{t('create_new_deck')}</span>
                </Button>
              }
            />
          </div>

          {/* Grid Decków */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {decks.map(deck => (
              <Card key={deck.id} className="flex flex-col min-h-[350px] shadow-lg relative">
                <CardHeader className="flex flex-col">
                  <div className="flex justify-between items-center space-x-4">
                    <CardTitle className="text-2xl font-bold truncate">{deck.name}</CardTitle>
                    {/* Collapsible Menu for Edit/Delete */}
                    <Collapsible
                      open={openCollapsibles[deck.id] || false}
                      onOpenChange={() => toggleCollapsible(deck.id)}
                    >
                      <CollapsibleTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="p-1 text-secondary hover:text-primary"
                          aria-label="Opcje"
                        >
                          <MoreVertical className="h-5 w-5" />
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="absolute right-4 top-16 bg-card border border-border rounded-md shadow-lg z-50 p-2">
                        <div className="flex flex-col">
                          <EditDeckDialog
                            deck={deck}
                            onSave={handleSave}
                            trigger={
                              <Button
                                variant="ghost"
                                size="sm"
                                className="flex items-center justify-start w-full px-4 py-2 hover:bg-secondary/80 text-primary"
                                onClick={(e: MouseEvent<HTMLButtonElement>) => {
                                  e.stopPropagation(); // Zapobiega propagacji zdarzenia
                                  setOpenCollapsibles(prev => ({ ...prev, [deck.id]: false })); // Zamknięcie Collapsible
                                }}
                              >
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
                              e.stopPropagation(); // Zapobiega propagacji zdarzenia
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
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleStudy(deck)}
                    className="flex items-center space-x-2 px-4 py-2"
                  >
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
