// components/FlashcardsPage.tsx

'use client'

import { useState, useEffect } from 'react'
import { EditDeckDialog } from '@/components/EditDeckDialog'
import axios from 'axios'
import { Button } from "@/components/ui/button"
import { PlusCircle, BookOpen, Loader2, Info, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { CustomTooltip } from '@/components/CustomTooltip'
import { StudyDeck } from '@/components/StudyDeck'
import { useTranslation } from 'react-i18next';
import React from 'react'

interface Flashcard {
  id?: number;
  question: string;
  answer: string;
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

  const { t } = useTranslation();

  // Define a base URL to maintain consistency
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
        // Creating a new deck
        const createDeckResponse = await axios.post<Deck>(API_BASE_URL, {
          name: updatedDeck.name,
          description: updatedDeck.description,
          flashcards: updatedDeck.flashcards.map(fc => ({
            question: fc.question,
            answer: fc.answer
          })),
        });
        const newDeck = createDeckResponse.data;
        setDecks(prevDecks => [...prevDecks, newDeck]);
      } else {
        // Updating an existing deck
        const updateDeckResponse = await axios.put<Deck>(`${API_BASE_URL}${updatedDeck.id}/`, {
          name: updatedDeck.name,
          description: updatedDeck.description,
          flashcards: updatedDeck.flashcards.map(fc => {
            if (fc.id) {
              return {
                id: fc.id,
                question: fc.question,
                answer: fc.answer
              };
            } else {
              return {
                question: fc.question,
                answer: fc.answer
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
      <div className="flex items-center justify-center h-screen">
        <Card className="w-[350px]">
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
    <div className="p-4 max-w-4xl mx-auto">
      <div className="text-center mb-6 flex items-center justify-center">
        <h1 className="text-3xl font-bold">{t('flashcards')}</h1>
          <CustomTooltip
            content={t('flashcards_tooltip')}
          >
            <Button variant="ghost" size="icon" className="ml-2">
              <Info className="h-4 w-4" />
              <span className="sr-only">{t('more_information')}</span>
            </Button>
          </CustomTooltip>
      </div>
      {decks.length === 0 ? (
        <Card className="w-full">
          <CardHeader>
            <CardTitle>{t('welcome_flashcards')}</CardTitle>
            <CardDescription>{t('get_started_create_deck')}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center space-y-4 py-8">
            <BookOpen className="h-24 w-24 text-muted-foreground" />
            <p className="text-center text-muted-foreground">
              {t('no_flashcard_decks')}
            </p>
          </CardContent>
          <CardFooter className="flex justify-center">
            <EditDeckDialog
              deck={{ id: 0, name: '', description: '', flashcards: [] }}
              onSave={handleSave}
              trigger={
                <Button>
                  <PlusCircle className="mr-2 h-4 w-4" />
                  {t('create_your_first_deck')}
                </Button>
              }
            />
          </CardFooter>
        </Card>
      ) : (
        <>
          <div className="mb-4 flex justify-end">
            <EditDeckDialog
              deck={{ id: 0, name: '', description: '', flashcards: [] }}
              onSave={handleSave}
              trigger={
                <Button>
                  <PlusCircle className="mr-2 h-4 w-4" />
                  {t('create_new_deck')}
                </Button>
              }
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {decks.map(deck => (
              <Card key={deck.id} className="flex flex-col">
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle>{deck.name}</CardTitle>
                    <div className="flex space-x-2">
                      <EditDeckDialog deck={deck} onSave={handleSave} trigger={<Button variant="outline" size="sm">{t('edit')}</Button>} />
                      <Button variant="destructive" size="sm" onClick={() => handleDelete(deck.id)}>{t('delete')}</Button>
                    </div>
                  </div>
                  <CardDescription>{deck.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{deck.flashcards.length} {t('flashcards_lowercase')}</p>
                </CardContent>
                <CardFooter className="mt-auto">
                  <Button variant="ghost" size="sm" className="ml-2" onClick={() => handleStudy(deck)}>
                    {t('study')} <ChevronRight className="ml-2 h-4 w-4" />
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
