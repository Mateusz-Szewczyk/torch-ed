// components/FlashcardsPage.tsx
'use client'

import { useState, useEffect, FormEvent } from 'react'
import { EditDeckDialog } from '@/components/EditDeckDialog'
import axios from 'axios'
import { Button } from "@/components/ui/button"
import { PlusCircle, BookOpen, Loader2, Info, ChevronRight, MoreVertical, Edit2, Trash2, Upload } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { CustomTooltip } from '@/components/CustomTooltip'
import { StudyDeck } from '@/components/StudyDeck'
import { useTranslation } from 'react-i18next';
import React from 'react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'

interface Flashcard {
  id?: number;
  question: string;
  answer: string;
  media_url?: string; // Nowe pole
}

interface Deck {
  id: number;
  name: string;
  description?: string;
  flashcards: Flashcard[];
}

export default function FlashcardsPage() {
  const [decks, setDecks] = useState<Deck[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [studyingDeck, setStudyingDeck] = useState<Deck | null>(null)
  const [importing, setImporting] = useState<boolean>(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [importSuccess, setImportSuccess] = useState<string | null>(null)

  const { t } = useTranslation();

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api/decks/'

  const fetchDecks = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get<Deck[]>(API_BASE_URL)
      setDecks(response.data)
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        setError(err.response.data.detail || t('error_fetch_decks'))
      } else {
        setError(t('error_unexpected_fetch_decks'))
      }
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDecks()
  }, [])

  const handleSave = async (updatedDeck: Deck) => {
    try {
      if (updatedDeck.id === 0) {
        // Create new deck
        const createDeckResponse = await axios.post<Deck>(API_BASE_URL, {
          name: updatedDeck.name,
          description: updatedDeck.description,
          flashcards: updatedDeck.flashcards.map(fc => ({
            question: fc.question,
            answer: fc.answer,
            media_url: fc.media_url // Nowe pole
          })),
        });
        const newDeck = createDeckResponse.data;
        setDecks(prevDecks => [...prevDecks, newDeck]);
      } else {
        // Update existing deck
        const updateDeckResponse = await axios.put<Deck>(`${API_BASE_URL}${updatedDeck.id}/`, {
          name: updatedDeck.name,
          description: updatedDeck.description,
          flashcards: updatedDeck.flashcards.map(fc => {
            if (fc.id) {
              return {
                id: fc.id,
                question: fc.question,
                answer: fc.answer,
                media_url: fc.media_url // Nowe pole
              };
            } else {
              return {
                question: fc.question,
                answer: fc.answer,
                media_url: fc.media_url // Nowe pole
              };
            }
          }),
        });
        const updatedDeckFromServer = updateDeckResponse.data;
        setDecks(prevDecks => prevDecks.map(deck =>
          deck.id === updatedDeckFromServer.id ? updatedDeckFromServer : deck
        ));
      }
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response) {
        console.error("Error saving deck:", error.response.data);
        setError(`${t('error_saving_deck')}: ${JSON.stringify(error.response.data)}`);
      } else {
        console.error("Error saving deck:", error);
        setError(t('error_unexpected_saving_deck'));
      }
    }
  };

  const handleDelete = async (deckId: number) => {
    try {
      await axios.delete(`${API_BASE_URL}${deckId}/`)
      setDecks(decks.filter(deck => deck.id !== deckId))
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        console.error("Error deleting deck:", err.response.data);
        setError(`${t('error_deleting_deck')}: ${err.response.data.detail || err.response.statusText}`);
      } else {
        console.error(err)
        setError(t('error_unexpected_deleting_deck'))
      }
    }
  }

  const handleStudy = (deck: Deck) => {
    setStudyingDeck(deck);
  }

  const handleExitStudy = () => {
    setStudyingDeck(null);
  }

  const handleImport = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const file = formData.get('file') as File

    if (!file) {
      setImportError(t('no_file_selected'))
      return
    }

    setImporting(true)
    setImportError(null)
    setImportSuccess(null)

    try {
      const response = await axios.post(`${API_BASE_URL}import/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      setImportSuccess(t('import_success'))
      fetchDecks()
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        setImportError(err.response.data.detail || t('import_failed'))
      } else {
        setImportError(t('import_failed'))
      }
      console.error(err)
    } finally {
      setImporting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="mr-2 h-16 w-16 animate-spin" />
        <span className="text-xl font-semibold">{t('loading_decks')}</span>
      </div>
    )
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
    )
  }

  if (studyingDeck) {
    return <StudyDeck deck={studyingDeck} onExit={handleExitStudy} />;
  }

  return (
    <div className="p-4 max-w-full mx-auto">
      {/* Header Section */}
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

      {/* No Decks Available */}
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
              {/* Przycisk Importu Fiszek */}
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="flex items-center space-x-2 px-6 py-3">
                    <Upload className="h-6 w-6" />
                    <span>{t('import_flashcards')}</span>
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <form onSubmit={handleImport} className="flex flex-col space-y-4">
                    <DialogHeader>
                      <DialogTitle>{t('import_flashcards')}</DialogTitle>
                      <DialogDescription>
                        {t('select_flashcards_file')}
                      </DialogDescription>
                    </DialogHeader>
                    <input
                      type="file"
                      name="file"
                      accept=".csv,.apkg"
                      required
                      className="border border-input rounded-md p-2"
                    />
                    {importError && <p className="text-red-500">{importError}</p>}
                    {importSuccess && <p className="text-green-500">{importSuccess}</p>}
                    <DialogFooter className="flex justify-end space-x-2">
                      <Button type="button" variant="ghost" onClick={() => { setImportError(null); setImportSuccess(null); }}>
                        {t('cancel')}
                      </Button>
                      <Button type="submit" disabled={importing}>
                        {importing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                        {t('import')}
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>

              {/* Przycisk Tworzenia Nowego Zestawu */}
              <EditDeckDialog
                deck={{ id: 0, name: '', description: '', flashcards: [] }}
                onSave={handleSave}
                trigger={
                  <Button className="flex items-center space-x-2 px-6 py-3">
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
          {/* Create New Deck and Import Flashcards Buttons */}
          <div className="mb-8 flex justify-end space-x-4">
            {/* Przycisk Importu Fiszek */}
            <Dialog>
              <DialogTrigger asChild>
                <Button className="flex items-center space-x-2 px-6 py-3">
                  <Upload className="h-6 w-6" />
                  <span>{t('import_flashcards')}</span>
                </Button>
              </DialogTrigger>
              <DialogContent>
                <form onSubmit={handleImport} className="flex flex-col space-y-4">
                  <DialogHeader>
                    <DialogTitle>{t('import_flashcards')}</DialogTitle>
                    <DialogDescription>
                      {t('select_flashcards_file')}
                    </DialogDescription>
                  </DialogHeader>
                  <input
                    type="file"
                    name="file"
                    accept=".csv,.apkg"
                    required
                    className="border border-input rounded-md p-2"
                  />
                  {importError && <p className="text-red-500">{importError}</p>}
                  {importSuccess && <p className="text-green-500">{importSuccess}</p>}
                  <DialogFooter className="flex justify-end space-x-2">
                    <Button type="button" variant="ghost" onClick={() => { setImportError(null); setImportSuccess(null); }}>
                      {t('cancel')}
                    </Button>
                    <Button type="submit" disabled={importing}>
                      {importing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      {t('import')}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>

            {/* Przycisk Tworzenia Nowego Zestawu */}
            <EditDeckDialog
              deck={{ id: 0, name: '', description: '', flashcards: [] }}
              onSave={handleSave}
              trigger={
                <Button className="flex items-center space-x-2 px-6 py-3">
                  <PlusCircle className="h-6 w-6" />
                  <span>{t('create_new_deck')}</span>
                </Button>
              }
            />
          </div>

          {/* Decks Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {decks.map(deck => (
              <Card key={deck.id} className="flex flex-col min-h-[350px] shadow-lg">
                <CardHeader className="flex flex-col">
                  <div className="flex justify-between items-center space-x-4">
                    <CardTitle className="text-2xl font-bold truncate">{deck.name}</CardTitle>
                    {/* Collapsible Menu for Edit/Delete */}
                    <Collapsible>
                      <CollapsibleTrigger asChild>
                        <Button variant="ghost" size="sm" className="p-1">
                          <MoreVertical className="h-5 w-5" />
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="absolute right-4 top-16 bg-card border border-border rounded-md shadow-lg z-50">
                        <div className="flex flex-col">
                          <EditDeckDialog
                            deck={deck}
                            onSave={handleSave}
                            trigger={
                              <Button
                                variant="ghost"
                                size="sm"
                                className="flex items-center justify-start w-full px-4 py-2 hover:bg-secondary/80"
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
                            onClick={() => handleDelete(deck.id)}
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
  )
}
