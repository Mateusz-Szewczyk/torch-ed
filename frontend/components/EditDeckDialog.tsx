'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Trash2 } from 'lucide-react'

interface Flashcard {
  id: number | null
  question: string
  answer: string
}

interface Deck {
  id: number
  name: string
  description?: string
  flashcards: Flashcard[]
}

interface EditDeckDialogProps {
  deck: Deck
  onSave: (updatedDeck: Deck) => void
  trigger: React.ReactNode
}

export const EditDeckDialog = ({ deck, onSave, trigger }: EditDeckDialogProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState(deck.name)
  const [description, setDescription] = useState(deck.description || '')
  const [flashcards, setFlashcards] = useState<Flashcard[]>(deck.flashcards)

  const handleAddFlashcard = () => {
    setFlashcards([...flashcards, { id: null, question: '', answer: '' }])
  }

  const handleFlashcardChange = (index: number, field: 'question' | 'answer', value: string) => {
    const updatedFlashcards = [...flashcards]
    updatedFlashcards[index][field] = value
    setFlashcards(updatedFlashcards)
  }

  const handleDeleteFlashcard = (index: number) => {
    const updatedFlashcards = flashcards.filter((_, i) => i !== index)
    setFlashcards(updatedFlashcards)
  }

  const handleSaveClick = (e: React.FormEvent) => {
    e.preventDefault()
    const updatedDeck: Deck = {
      ...deck,
      name,
      description,
      flashcards,
    }
    onSave(updatedDeck)
    setIsOpen(false)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {trigger}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{deck.id === 0 ? 'Create New Deck' : 'Edit Deck'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSaveClick} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="deck-name">Deck Name</Label>
            <Input
              id="deck-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter deck name"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="deck-description">Deck Description</Label>
            <Textarea
              id="deck-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter deck description"
            />
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-2">Flashcards:</h3>
            {flashcards.map((fc, index) => (
              <div key={index} className="border rounded-md p-4 mb-4 space-y-2">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium">Flashcard {index + 1}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteFlashcard(index)}
                    aria-label={`Delete flashcard ${index + 1}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`flashcard-question-${index}`}>Question</Label>
                  <Input
                    id={`flashcard-question-${index}`}
                    value={fc.question}
                    onChange={(e) => handleFlashcardChange(index, 'question', e.target.value)}
                    placeholder="Enter the question"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`flashcard-answer-${index}`}>Answer</Label>
                  <Textarea
                    id={`flashcard-answer-${index}`}
                    value={fc.answer}
                    onChange={(e) => handleFlashcardChange(index, 'answer', e.target.value)}
                    placeholder="Enter the answer"
                    required
                  />
                </div>
              </div>
            ))}
            <Button type="button" variant="outline" onClick={handleAddFlashcard} className="w-full mt-2">
              Add Flashcard
            </Button>
          </div>
          <div className="flex justify-end space-x-2">
            <Button type="button" variant="ghost" onClick={() => setIsOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">
              Save
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

