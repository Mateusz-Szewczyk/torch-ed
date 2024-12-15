// components/EditTestDialog.tsx
'use client'

import React, { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useTranslation } from 'react-i18next'

interface Test {
  id: number;
  name: string;
  description?: string;
  questions: Question[];
}

interface Question {
  id?: number;
  question: string;
  answer: string;
}

interface EditTestDialogProps {
  test: Test;
  onSave: (updatedTest: Test) => void;
  trigger: React.ReactElement;
}

export function EditTestDialog({ test, onSave, trigger }: EditTestDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState(test.name)
  const [description, setDescription] = useState(test.description || '')
  const { t } = useTranslation()

  const handleSave = () => {
    const updatedTest: Test = {
      ...test,
      name,
      description,
      // Zakładając, że pytania są edytowane osobno
    }
    onSave(updatedTest)
    setIsOpen(false)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{test.id === 0 ? t('create_test') : t('edit_test')}</DialogTitle>
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
          {/* Możesz dodać pola do edycji pytań, jeśli jest to potrzebne */}
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
