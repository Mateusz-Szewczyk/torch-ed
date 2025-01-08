// src/components/EditExamDialog.tsx

'use client';

import React, { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useTranslation } from 'react-i18next';
import { Exam } from '@/types';

interface EditExamDialogProps {
  exam: Exam;
  onSave: (updatedExam: Exam) => void;
  trigger: React.ReactElement;
}

export function EditExamDialog({ exam, onSave, trigger }: EditExamDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState(exam.name);
  const [description, setDescription] = useState(exam.description || '');
  const { t } = useTranslation();

  const handleSave = () => {
    const updatedExam: Exam = {
      ...exam,
      name,
      description,
      // Dodaj logikę do edycji pytań i odpowiedzi, jeśli potrzebne
    };
    onSave(updatedExam);
    setIsOpen(false);
  };

  useEffect(() => {
    setName(exam.name);
    setDescription(exam.description || '');
  }, [exam]);

  return (
    <>
      {/* Trigger Button */}
      {React.cloneElement(trigger, { onClick: () => setIsOpen(true) })}

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{exam.id === 0 ? t('create_new_test') : t('edit_test')}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              handleSave();
            }}
            className="space-y-4 mt-4"
          >
            {/* Pole Nazwy Egzaminu */}
            <div>
              <label htmlFor="exam-name" className="block text-sm font-medium mb-1">
                {t('test_name')}
              </label>
              <Input
                id="exam-name"
                value={name}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
                placeholder={t('enter_test_name')}
                required
              />
            </div>

            {/* Pole Opisu Egzaminu */}
            <div>
              <label htmlFor="exam-description" className="block text-sm font-medium mb-1">
                {t('test_description')}
              </label>
              <Textarea
                id="exam-description"
                value={description}
                onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
                placeholder={t('enter_test_description')}
              />
            </div>

            {/* Możesz dodać pola do edycji pytań i odpowiedzi, jeśli jest to potrzebne */}

            <DialogFooter>
              <Button type="button" variant="secondary" onClick={() => setIsOpen(false)}>
                {t('cancel')}
              </Button>
              <Button type="submit" variant="default">
                {t('save')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default EditExamDialog;
