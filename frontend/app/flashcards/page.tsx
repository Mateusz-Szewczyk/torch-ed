'use client'

import { useState, useEffect } from 'react'
import { EditDeckDialog } from '@/components/EditDeckDialog'
import axios from 'axios'
import { Button } from "@/components/ui/button"
import { PlusCircle, BookOpen, Loader2, Info, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { CustomTooltip } from '@/components/CustomTooltip'
import { StudyDeck } from '@/components/StudyDeck'

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

  const fetchDecks = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get<Deck[]>('http://localhost:8043/api/decks/')
      setDecks(response.data)
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        setError(err.response.data.detail || 'An error occurred while fetching decks.')
      } else {
        setError('An unexpected error occurred while fetching decks.')
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
        // Tworzenie nowego zestawu (deck)
        const createDeckResponse = await axios.post<Deck>('http://localhost:8043/decks/', {
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
        // Aktualizacja istniejącego zestawu (deck)
        const updateDeckResponse = await axios.put<Deck>(`http://localhost:8043/decks/${updatedDeck.id}/`, {
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
        setError(`Error: ${JSON.stringify(error.response.data)}`);
      } else {
        console.error("Error saving deck:", error);
        setError('An error occurred while saving the deck.');
      }
    }
  };

  const handleDelete = async (deckId: number) => {
    try {
      await axios.delete(`http://localhost:8043/decks/${deckId}/`)
      setDecks(decks.filter(deck => deck.id !== deckId))
    } catch (err: unknown) {
      console.error(err)
      setError('An error occurred while deleting the deck.')
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
        <span className="text-xl font-semibold">Loading decks...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Card className="w-[350px]">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchDecks}>Try Again</Button>
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
        <h1 className="text-3xl font-bold">Flashcards</h1>
          <CustomTooltip
            content='Need Flashcards? Chat can help you produce study-ready flashcards in seconds. Sample Request: "Generate 10 flashcards to help me with my math exam preparation."'
          >
            <Button variant="ghost" size="icon" className="ml-2">
              <Info className="h-4 w-4" />
              <span className="sr-only">More information</span>
            </Button>
          </CustomTooltip>
      </div>
      {decks.length === 0 ? (
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Welcome to Flashcards!</CardTitle>
            <CardDescription>Get started by creating your first deck.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center space-y-4 py-8">
            <BookOpen className="h-24 w-24 text-muted-foreground" />
            <p className="text-center text-muted-foreground">
              You don't have any flashcard decks yet. Create a new deck to begin your learning journey!
            </p>
          </CardContent>
          <CardFooter className="flex justify-center">
            <EditDeckDialog
              deck={{ id: 0, name: '', description: '', flashcards: [] }}
              onSave={handleSave}
              trigger={
                <Button>
                  <PlusCircle className="mr-2 h-4 w-4" />
                  Create Your First Deck
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
                  Create New Deck
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
                      <EditDeckDialog deck={deck} onSave={handleSave} trigger={<Button variant="outline" size="sm">Edit</Button>} />
                      <Button variant="destructive" size="sm" onClick={() => handleDelete(deck.id)}>Delete</Button>
                    </div>
                  </div>
                  <CardDescription>{deck.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{deck.flashcards.length} flashcards</p>
                </CardContent>
                <CardFooter className="mt-auto">
                  <Button variant="ghost" size="sm" className="ml-2" onClick={() => handleStudy(deck)}>
                    Study <ChevronRight className="ml-2 h-4 w-4" />
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
