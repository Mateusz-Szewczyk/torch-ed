'use client'

import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ChevronLeft } from 'lucide-react'

type Flashcard = {
  id: number
  question: string
  answer: string
}

type Deck = {
  id: number
  name: string
  cards: Flashcard[]
}

const decks: Deck[] = [
  {
    id: 1,
    name: "General Knowledge",
    cards: [
      { id: 1, question: "What is the capital of France?", answer: "Paris" },
      { id: 2, question: "Who painted the Mona Lisa?", answer: "Leonardo da Vinci" },
      { id: 3, question: "What is the largest planet in our solar system?", answer: "Jupiter" },
    ]
  },
  {
    id: 2,
    name: "Science",
    cards: [
      { id: 1, question: "What is the chemical symbol for water?", answer: "H2O" },
      { id: 2, question: "What is the largest organ in the human body?", answer: "Skin" },
      { id: 3, question: "What is the speed of light?", answer: "299,792,458 meters per second" },
    ]
  },
  {
    id: 3,
    name: "History",
    cards: [
      { id: 1, question: "In which year did World War II end?", answer: "1945" },
      { id: 2, question: "Who was the first President of the United States?", answer: "George Washington" },
      { id: 3, question: "What ancient wonder was located in Alexandria?", answer: "The Lighthouse of Alexandria" },
    ]
  }
]

export default function Flashcards() {
  const [selectedDeck, setSelectedDeck] = useState<Deck | null>(null)
  const [currentCardIndex, setCurrentCardIndex] = useState(0)
  const [showAnswer, setShowAnswer] = useState(false)

  const handleDeckSelect = (deck: Deck) => {
    setSelectedDeck(deck)
    setCurrentCardIndex(0)
    setShowAnswer(false)
  }

  const handleNextCard = () => {
    if (selectedDeck) {
      setCurrentCardIndex((prevIndex) => (prevIndex + 1) % selectedDeck.cards.length)
      setShowAnswer(false)
    }
  }

  const handlePrevCard = () => {
    if (selectedDeck) {
      setCurrentCardIndex((prevIndex) => (prevIndex - 1 + selectedDeck.cards.length) % selectedDeck.cards.length)
      setShowAnswer(false)
    }
  }

  const toggleAnswer = () => {
    setShowAnswer(!showAnswer)
  }

  const returnToDeckSelection = () => {
    setSelectedDeck(null)
    setCurrentCardIndex(0)
    setShowAnswer(false)
  }

  return (
    <div className="h-full flex flex-col items-center justify-center p-4 bg-background text-foreground">
      {selectedDeck ? (
        <>
          <div className="w-full max-w-md mb-4">
            <Button variant="ghost" onClick={returnToDeckSelection} className="mb-4">
              <ChevronLeft className="mr-2 h-4 w-4" />
              Back to Decks
            </Button>
            <h1 className="text-2xl font-bold mb-6">{selectedDeck.name}</h1>
          </div>
          <Card className="w-full max-w-md bg-card text-card-foreground">
            <CardContent className="p-6">
              <div className="text-center mb-4">
                <h2 className="text-xl font-semibold mb-2">
                  {showAnswer ? "Answer" : "Question"}
                </h2>
                <p className="text-lg">
                  {showAnswer ? selectedDeck.cards[currentCardIndex].answer : selectedDeck.cards[currentCardIndex].question}
                </p>
              </div>
              <div className="flex justify-center space-x-2">
                <Button onClick={handlePrevCard} variant="outline">Previous</Button>
                <Button onClick={toggleAnswer} variant="outline">
                  {showAnswer ? "Show Question" : "Show Answer"}
                </Button>
                <Button onClick={handleNextCard} variant="outline">Next</Button>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <div className="w-full max-w-md">
          <h1 className="text-2xl font-bold mb-6">Choose a Flashcard Deck</h1>
          <div className="space-y-4">
            {decks.map((deck) => (
              <Button
                key={deck.id}
                onClick={() => handleDeckSelect(deck)}
                variant="outline"
                className="w-full justify-start text-left h-auto py-4"
              >
                <div>
                  <div className="font-semibold">{deck.name}</div>
                  <div className="text-sm text-muted-foreground">{deck.cards.length} cards</div>
                </div>
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

