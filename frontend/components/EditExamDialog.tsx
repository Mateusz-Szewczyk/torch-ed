// src/components/EditExamDialog.tsx
'use client'

import React, { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useTranslation } from 'react-i18next'
import { Exam, ExamQuestion, ExamAnswer } from '../schemas'

interface EditExamDialogProps {
  exam: Exam;
  onSave: (updatedExam: Exam) => void;
  trigger: React.ReactElement;
}

export function EditExamDialog({ exam, onSave, trigger }: EditExamDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState(exam.name)
  const [description, setDescription] = useState(exam.description || '')
  const { t } = useTranslation()

  const handleSave = () => {
    const updatedExam: Exam = {
      ...exam,
      name,
      description,
      // Możesz dodać logikę do edycji pytań i odpowiedzi
    }
    onSave(updatedExam)
    setIsOpen(false)
  }

  useEffect(() => {
    setName(exam.name)
    setDescription(exam.description || '')
  }, [exam])

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{exam.id === 0 ? t('create_new_test') : t('edit_test')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <Input
            label={t('test_name')}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('enter_test_name')}
          />
          <Textarea
            label={t('test_description')}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t('enter_test_description')}
          />
          {/* Możesz dodać pola do edycji pytań i odpowiedzi, jeśli jest to potrzebne */}
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => setIsOpen(false)}>
            {t('cancel')}
          </Button>
          <Button variant="primary" onClick={handleSave}>
            {t('save')}
          </Button>
        </DialogFooter>
      </DialogContent>
      {/* Trigger Button */}
      {React.cloneElement(trigger, { onClick: () => setIsOpen(true) })}
    </Dialog>
  )
}
