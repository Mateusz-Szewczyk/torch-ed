// src/components/FeedbackModal.tsx

'use client';

import React, { useState, useEffect } from 'react';
import { useForm, ValidationError } from '@formspree/react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useTranslation } from 'react-i18next';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const [state, handleFormSubmit] = useForm("xvgojkjv");
  const [selectedSource, setSelectedSource] = useState<string>('');
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const [showImprovementSuggestions, setShowImprovementSuggestions] = useState<boolean>(false);

  useEffect(() => {
    // Pokazuje pole sugestii, jeśli wybrano przynajmniej jedną funkcję
    if (selectedFeatures.length > 0) {
      setShowImprovementSuggestions(true);
    } else {
      setShowImprovementSuggestions(false);
    }
  }, [selectedFeatures]);

  if (!isOpen) return null;

  // Lista funkcji z pliku tłumaczeń
  const features = [
    { value: 'Flashcards', label: t('features_list.Flashcards') },
    { value: 'Exams', label: t('features_list.Exams') },
    { value: 'Chatbot', label: t('features_list.Chatbot') },
    { value: 'Flashcard Generation', label: t('features_list.Flashcard Generation') },
    { value: 'Exams Generation', label: t('features_list.Exams Generation') },
    { value: 'Statistics', label: t('features_list.Statistics') },
    { value: 'File saving', label: t('features_list.File saving') },
  ];

  // Obsługa zmiany w checkboxes
  const handleFeatureChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value, checked } = e.target;
    if (checked) {
      setSelectedFeatures([...selectedFeatures, value]);
    } else {
      setSelectedFeatures(selectedFeatures.filter(feature => feature !== value));
    }
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
        {state.succeeded ? (
          <p className="text-green-500 text-center">{t('feedback_thanks')}</p>
        ) : (
          <form onSubmit={handleFormSubmit} className="space-y-4 p-4">
            {/* Pierwsze Pole: Skąd dowiedziałeś się o naszej stronie? */}
            <div>
              <label htmlFor="source" className="block text-sm font-medium mb-1">
                {t('source_question')}
              </label>
              <select
                id="source"
                name="source"
                className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
                required
              >
                <option value="" disabled>{t('select_option')}</option>
                <option value="Od znajomych lub rodziny">{t('source_friend')}</option>
                <option value="Od twórców strony">{t('source_creator')}</option>
                <option value="Za pomocą wyszukiwarki internetowej">{t('source_search')}</option>
                <option value="Inne">{t('source_other')}</option>
              </select>
              <ValidationError
                prefix="Source"
                field="source"
                errors={state.errors}
              />
            </div>

            {/* Dodatkowe Pole: Jeśli wybrano "Inne" */}
            {selectedSource === 'Inne' && (
              <div>
                <label htmlFor="otherSource" className="block text-sm font-medium mb-1">
                  {t('other_source_placeholder')}
                </label>
                <input
                  id="otherSource"
                  type="text"
                  name="otherSource"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
                  placeholder={t('other_source_placeholder')}
                  required
                />
                <ValidationError
                  prefix="Other Source"
                  field="otherSource"
                  errors={state.errors}
                />
              </div>
            )}

            {/* Drugie Pole: Jak oceniasz aktualne funkcje naszej strony? */}
            <div>
              <label htmlFor="featuresRating" className="block text-sm font-medium mb-1">
                {t('features_rating_question')}
              </label>
              <select
                id="featuresRating"
                name="featuresRating"
                className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
                required
              >
                <option value="" disabled>{t('select_option')}</option>
                <option value="1">1 - {t('very_dissatisfied')}</option>
                <option value="2">2 - {t('dissatisfied')}</option>
                <option value="3">3 - {t('neutral')}</option>
                <option value="4">4 - {t('satisfied')}</option>
                <option value="5">5 - {t('very_satisfied')}</option>
              </select>
              <ValidationError
                prefix="Features Rating"
                field="featuresRating"
                errors={state.errors}
              />
            </div>

            {/* Szczegółowe Pytanie o Funkcje */}
            <div>
              <label htmlFor="featuresFeedback" className="block text-sm font-medium mb-1">
                {t('likes_features_question')}
              </label>
              <div className="space-y-2">
                {features.map(feature => (
                  <div key={feature.value} className="flex items-center">
                    <input
                      id={feature.value}
                      type="checkbox"
                      name="features"
                      value={feature.value}
                      checked={selectedFeatures.includes(feature.value)}
                      onChange={handleFeatureChange}
                      className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <label htmlFor={feature.value} className="ml-2 text-sm text-gray-700 dark:text-gray-200">
                      {feature.label}
                    </label>
                  </div>
                ))}
              </div>
              <ValidationError
                prefix="Features"
                field="features"
                errors={state.errors}
              />
            </div>

            {/* Dodatkowe Pole: Sugestie dotyczące ulepszenia wybranych funkcji */}
            {showImprovementSuggestions && (
              <div>
                <label htmlFor="featuresImprovement" className="block text-sm font-medium mb-1">
                  {t('features_improvement_suggestions')}
                </label>
                <Textarea
                  id="featuresImprovement"
                  name="featuresImprovement"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
                  rows={4}
                  placeholder={t('suggestion_placeholder')}
                />
                <ValidationError
                  prefix="Features Improvement"
                  field="featuresImprovement"
                  errors={state.errors}
                />
              </div>
            )}

            {/* Trzecie Pole: Czy masz pomysł na nową funkcjonalność? */}
            <div>
              <label htmlFor="newFeature" className="block text-sm font-medium mb-1">
                {t('new_feature_question')}
              </label>
              <Textarea
                id="newFeature"
                name="newFeature"
                className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
                rows={4}
                placeholder={t('your_feedback')}
              />
              <ValidationError
                prefix="New Feature"
                field="newFeature"
                errors={state.errors}
              />
            </div>

            {/* Net Promoter Score (NPS) */}
            <div>
              <label htmlFor="nps" className="block text-sm font-medium mb-1">
                {t('nps_question')}
              </label>
              <select
                id="nps"
                name="nps"
                className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
                required
              >
                <option value="" disabled>{t('select_option')}</option>
                {[...Array(11)].map((_, index) => (
                  <option key={index} value={index}>{index}</option>
                ))}
              </select>
              <ValidationError
                prefix="NPS"
                field="nps"
                errors={state.errors}
              />
            </div>

            {/* Łatwość Użytkowania */}
            <div>
              <label htmlFor="usability" className="block text-sm font-medium mb-1">
                {t('usability_question')}
              </label>
              <select
                id="usability"
                name="usability"
                className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
                required
              >
                <option value="" disabled>{t('select_option')}</option>
                <option value="1">1 - {t('very_difficult')}</option>
                <option value="2">2 - {t('difficult')}</option>
                <option value="3">3 - {t('neutral')}</option>
                <option value="4">4 - {t('easy')}</option>
                <option value="5">5 - {t('very_easy')}</option>
              </select>
              <ValidationError
                prefix="Usability"
                field="usability"
                errors={state.errors}
              />
            </div>


            {/* Przycisk Submit */}
            <Button type="submit" disabled={state.submitting} className="w-full">
              {state.submitting ? t('sending') : t('submit')}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default FeedbackModal;
