'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2, Info } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CustomTooltip } from '@/components/CustomTooltip';

interface ImportFlashcardsModalProps {
  trigger: React.ReactElement;
  onImportSuccess?: () => void;
}

export const ImportFlashcardsModal = ({ trigger, onImportSuccess }: ImportFlashcardsModalProps) => {
  const { t } = useTranslation();

  const [isOpen, setIsOpen] = useState(false);
  const [importing, setImporting] = useState<boolean>(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';
  const API_BASE_URL = `${API_URL}/decks/`;

  const handleImport = async (e: React.FormEvent<HTMLFormElement>) => {
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
        const errorData: unknown = await response.json();
        let errorMessage = 'Nie udało się zaimportować fiszek.';
        if (
          typeof errorData === 'object' &&
          errorData !== null &&
          'detail' in errorData
        ) {
          const { detail } = errorData as { detail: unknown };
          if (Array.isArray(detail)) {
            errorMessage = detail
              .map((err) => {
                if (typeof err === 'object' && err !== null && 'msg' in err) {
                  const msg = (err as { msg: unknown }).msg;
                  return typeof msg === 'string' ? msg : String(msg);
                } else {
                  return String(err);
                }
              })
              .join(', ');
          } else if (typeof detail === 'string') {
            errorMessage = detail;
          }
        }
        throw new Error(errorMessage);
      }

      setImportSuccess(t('import_success'));
      if (onImportSuccess) {
        onImportSuccess();
      }
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

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger>{trigger}</DialogTrigger>
      <DialogContent className="bg-background text-foreground p-6 rounded-lg max-w-md w-full">
        <form onSubmit={handleImport} className="flex flex-col space-y-4">
          <DialogHeader className="flex flex-row items-center justify-between">
            <div>
              <DialogTitle>{t('import_flashcards')}</DialogTitle>
              <DialogDescription>{t('select_flashcards_file')}</DialogDescription>
            </div>
            <CustomTooltip content="Tutaj wgrywasz fiszki (CSV, APKG lub TXT). Możesz też ustawić nazwę i opis, które pojawią się jako nowa talia.">
              <Info className="h-5 w-5 text-muted-foreground cursor-pointer" />
            </CustomTooltip>
          </DialogHeader>

          {/* Pola dodatkowe: opcjonalna nazwa i opis talii */}
          <div className="flex flex-col">
            <label className="font-medium">{t('deck_name')}</label>
            <input
              type="text"
              name="deck_name"
              placeholder={t('optional_deck_name') || 'Opcjonalna nazwa talii'}
              className="border border-input rounded-md p-2"
            />
          </div>
          <div className="flex flex-col">
            <label className="font-medium">{t('deck_description')}</label>
            <textarea
              name="deck_description"
              placeholder={t('optional_deck_description') || 'Opcjonalny opis talii'}
              className="border border-input rounded-md p-2"
              rows={3}
            />
          </div>
          <div className="flex flex-col">
            <label className="font-medium">{t('select_file')}</label>
            <input
              type="file"
              name="file"
              accept=".csv,.apkg,.txt"
              required
              className="border border-input rounded-md p-2"
            />
          </div>

          {importError && <p className="text-red-500 text-sm">{importError}</p>}
          {importSuccess && <p className="text-green-500 text-sm">{importSuccess}</p>}

          <DialogFooter className="flex flex-col md:flex-row justify-end space-y-2 md:space-y-0 md:space-x-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setImportError(null);
                setImportSuccess(null);
                setIsOpen(false);
              }}
              className="w-full md:w-auto"
            >
              {t('cancel')}
            </Button>
            <Button type="submit" disabled={importing} className="w-full md:w-auto">
              {importing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('import')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
