'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Trash2, Plus } from 'lucide-react'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"

interface EditDeckDialogProps {
  deck: { id: number; name: string; cards: { id: number; question: string; answer: string }[] }
  onSave: (id: number, name: string, cards: { id: number; question: string; answer: string }[]) => void
  trigger: React.ReactNode
}

export function EditDeckDialog({ deck, onSave, trigger }: EditDeckDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState(deck.name)
  const [cards, setCards] = useState(deck.cards)

  const handleSave = () => {
    onSave(deck.id, name, cards)
    setIsOpen(false)
  }

  const handleAddCard = () => {
    setCards([...cards, { id: Date.now(), question: '', answer: '' }])
  }

  const handleDeleteCard = (id: number) => {
    setCards(cards.filter(card => card.id !== id))
  }

  const handleUpdateCard = (id: number, field: 'question' | 'answer', value: string) => {
    setCards(cards.map(card => card.id === id ? { ...card, [field]: value } : card))
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-[600px] bg-background text-foreground">
        <DialogHeader>
          <DialogTitle className="text-foreground">Edit Deck: {name}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="deckName">Deck Name</Label>
            <Input
              id="deckName"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="col-span-3"
            />
          </div>
          {cards.map((card, index) => (
            <div key={card.id} className="grid gap-2 p-4 border rounded-md">
              <div className="flex justify-between items-center">
                <Label>Flashcard {index + 1}</Label>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline" size="icon">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This action cannot be undone. This will permanently delete this flashcard.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={() => handleDeleteCard(card.id)}>Delete</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
              <Input
                value={card.question}
                onChange={(e) => handleUpdateCard(card.id, 'question', e.target.value)}
                placeholder="Question"
                className="col-span-3"
              />
              <Input
                value={card.answer}
                onChange={(e) => handleUpdateCard(card.id, 'answer', e.target.value)}
                placeholder="Answer"
                className="col-span-3"
              />
            </div>
          ))}
          <Button onClick={handleAddCard} variant="outline">
            <Plus className="mr-2 h-4 w-4" />
            Add Flashcard
          </Button>
        </div>
        <Button onClick={handleSave}>Save Changes</Button>
      </DialogContent>
    </Dialog>
  )
}

