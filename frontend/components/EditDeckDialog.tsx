// components/EditDeckDialog.tsx

'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Flashcard {
  id: number;
  question: string;
  answer: string;
}

interface Deck {
  id: number;
  name: string;
  description?: string;
  flashcards: Flashcard[];
}

interface EditDeckDialogProps {
  deck: Deck;
  onSave: (updatedDeck: Deck) => void;
  trigger: React.ReactNode;
}

export const EditDeckDialog = ({ deck, onSave, trigger }: EditDeckDialogProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState(deck.name);
  const [description, setDescription] = useState(deck.description || '');
  const [flashcards, setFlashcards] = useState<Flashcard[]>(deck.flashcards);

  const { t } = useTranslation();

  useEffect(() => {
    if (isOpen) {
      setName(deck.name);
      setDescription(deck.description || '');
      setFlashcards(deck.flashcards);
    }
  }, [isOpen, deck]);

  const handleAddFlashcard = () => {
    // Dodanie nowej fiszki na górę listy
    setFlashcards([{ id: Date.now(), question: '', answer: '' }, ...flashcards]);
  };

  const handleFlashcardChange = (index: number, field: 'question' | 'answer', value: string) => {
    setFlashcards((prevFlashcards) =>
      prevFlashcards.map((fc, i) =>
        i === index ? { ...fc, [field]: value } : fc
      )
    );
  };

  const handleDeleteFlashcard = (index: number) => {
    setFlashcards((prevFlashcards) => prevFlashcards.filter((_, i) => i !== index));
  };

  const handleSaveClick = (e: React.FormEvent) => {
    e.preventDefault();

    if (name.trim() === '' || flashcards.some(fc => fc.question.trim() === '' || fc.answer.trim() === '')) {
      alert(t('error_provide_deck_and_flashcards'));
      return;
    }

    const updatedDeck: Deck = {
      ...deck,
      name,
      description,
      flashcards: flashcards.map((fc, index) => ({
        ...fc,
        id: fc.id || index + 1
      })),
    };

    onSave(updatedDeck);
    setIsOpen(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-[600px] bg-background text-foreground p-6 rounded-lg flex flex-col">
        <DialogHeader>
          <DialogTitle>{deck.id === 0 ? t('create_new_deck') : t('edit_deck')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSaveClick} className="flex flex-col flex-grow">
          <div className="space-y-4 flex-grow overflow-y-auto">
            <div className="space-y-2">
              <Label htmlFor="deck-name">{t('deck_name')}</Label>
              <Input
                id="deck-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('enter_deck_name')}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="deck-description">{t('deck_description')}</Label>
              <Textarea
                id="deck-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t('enter_deck_description')}
              />
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">{t('flashcards')}:</h3>
              {/* Przycisk dodawania fiszki na górze */}
              <Button
                type="button"
                variant="outline"
                onClick={handleAddFlashcard}
                className="w-full mb-4 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {t('add_flashcard')}
              </Button>
              {/* Lista fiszek */}
              {flashcards.map((fc, index) => (
                <div key={fc.id} className="border rounded-md p-4 mb-4 space-y-2 bg-background">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">{t('flashcard_number', { number: index + 1 })}</span>
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDeleteFlashcard(index)}
                      aria-label={t('delete_flashcard', { number: index + 1 })}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`flashcard-question-${fc.id}`}>{t('question')}</Label>
                    <Input
                      id={`flashcard-question-${fc.id}`}
                      value={fc.question}
                      onChange={(e) => handleFlashcardChange(index, 'question', e.target.value)}
                      placeholder={t('enter_question')}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`flashcard-answer-${fc.id}`}>{t('answer')}</Label>
                    <Textarea
                      id={`flashcard-answer-${fc.id}`}
                      value={fc.answer}
                      onChange={(e) => handleFlashcardChange(index, 'answer', e.target.value)}
                      placeholder={t('enter_answer')}
                      required
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          {/* Przycisk Zapisz i Anuluj przyklejony do dołu */}
          <div className="mt-4 flex justify-end space-x-2">
            <Button type="button" variant="ghost" onClick={() => setIsOpen(false)}>
              {t('cancel')}
            </Button>
            <Button type="submit">{t('save')}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
