// src/components/DeckCard.tsx

import React from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MoreVertical, Edit2, Trash2, ChevronRight } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { EditDeckDialog } from '@/components/EditDeckDialog';
import { useTranslation } from 'react-i18next';
import { Deck } from '@/types'; // Import interfejsu Deck z centralnego pliku

interface DeckCardProps {
  deck: Deck;
  isOpen: boolean;
  onToggle: (deckId: number, isOpen: boolean) => void;
  onSave: (updatedDeck: Deck) => void;
  onDelete: (deckId: number) => void;
  onStudy: (deck: Deck) => void;
}

const DeckCard: React.FC<DeckCardProps> = ({ deck, isOpen, onToggle, onSave, onDelete, onStudy }) => {
  const { t } = useTranslation();

  const handleEditSave = (updatedDeck: Deck) => {
    onSave(updatedDeck);
    onToggle(deck.id, false); // Zamknięcie Collapsible po zapisaniu
  };

  const handleDeleteClick = () => {
    onDelete(deck.id);
    onToggle(deck.id, false); // Zamknięcie Collapsible po usunięciu
  };

  return (
    <Card className="flex flex-col min-h-[350px] shadow-lg">
      <CardHeader className="flex flex-col">
        <div className="flex justify-between items-center space-x-4 relative">
          <CardTitle className="text-2xl font-bold truncate">{deck.name}</CardTitle>
          <Collapsible
            open={isOpen}
            onOpenChange={(isOpen) => onToggle(deck.id, isOpen)}
          >
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="p-1">
                <MoreVertical className="h-5 w-5" />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="absolute right-4 top-16 bg-card border border-border rounded-md shadow-lg z-50 p-2">
              <div className="flex flex-col">
                <EditDeckDialog
                  deck={deck}
                  onSave={handleEditSave}
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
                  onClick={handleDeleteClick}
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
          onClick={() => onStudy(deck)}
          className="flex items-center space-x-2 px-4 py-2"
        >
          <span>{t('study')}</span>
          <ChevronRight className="h-5 w-5" />
        </Button>
      </CardFooter>
    </Card>
  );
};

export default DeckCard;
