// src/components/FeedbackModal.tsx

'use client';

import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useTranslation } from 'react-i18next';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const [feedback, setFeedback] = React.useState('');

  const handleSubmit = () => {
    // Logika wysyłania feedbacku
    console.log('Feedback submitted:', feedback);
    setFeedback('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('send_feedback')}</DialogTitle>
          <DialogDescription>
            {t('provide_your_feedback_below')}
          </DialogDescription>
        </DialogHeader>
        <div className="p-4">
          <Textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder={t('your_feedback')}
            className="w-full"
          />
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>
            {t('cancel')}
          </Button>
          <Button variant="default" onClick={handleSubmit} disabled={!feedback.trim()}>
            {t('submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default FeedbackModal;
