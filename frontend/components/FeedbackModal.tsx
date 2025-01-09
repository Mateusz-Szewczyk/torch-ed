// src/components/FeedbackModal.tsx

'use client';

import React, { useState, useEffect } from 'react';
import { useForm, ValidationError } from '@formspree/react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useTranslation } from 'react-i18next';
import { ScrollArea } from '@/components/ui/scroll-area'; // Importowanie ScrollArea

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

  // Sprawdzenie, czy `state.errors` jest tablicą
  const hasErrors = Array.isArray(state.errors) && state.errors.length > 0;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl w-full h-[80vh] p-0">
        <div className="flex flex-col h-full">
          <DialogHeader className="p-6 border-b border-gray-200 dark:border-gray-700">
            <DialogTitle className="text-2xl font-semibold text-gray-800 dark:text-gray-200">
              {t('send_feedback')}
            </DialogTitle>
            <DialogDescription className="mt-2 text-gray-600 dark:text-gray-400">
              {t('feedback_description')}
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="flex-1 p-6">
            {state.succeeded ? (
              <div className="flex flex-col items-center justify-center h-full">
                <p className="text-green-600 dark:text-green-400 text-lg mb-4">
                  {t('feedback_thanks')}
                </p>
                <Button onClick={onClose}>
                  {t('close')}
                </Button>
              </div>
            ) : (
              <form onSubmit={handleFormSubmit} className="space-y-6">
                {/* Skąd dowiedziałeś się o naszej stronie? */}
                <div>
                  <label htmlFor="source" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('source_question')}
                  </label>
                  <select
                    id="source"
                    name="source"
                    className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-200"
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
                    className="text-red-500 text-sm mt-1"
                  />
                </div>

                {/* Jeśli wybrano "Inne" */}
                {selectedSource === 'Inne' && (
                  <div>
                    <label htmlFor="otherSource" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      {t('other_source_placeholder')}
                    </label>
                    <input
                      id="otherSource"
                      type="text"
                      name="otherSource"
                      className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-200"
                      placeholder={t('other_source_placeholder')}
                      required
                    />
                    <ValidationError
                      prefix="Other Source"
                      field="otherSource"
                      errors={state.errors}
                      className="text-red-500 text-sm mt-1"
                    />
                  </div>
                )}

                {/* Jak oceniasz aktualne funkcje naszej strony? */}
                <div>
                  <label htmlFor="featuresRating" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('features_rating_question')}
                  </label>
                  <select
                    id="featuresRating"
                    name="featuresRating"
                    className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-200"
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
                    className="text-red-500 text-sm mt-1"
                  />
                </div>

                {/* Które z poniższych funkcji najbardziej Ci się podobają? */}
                <div>
                  <label htmlFor="featuresFeedback" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('likes_features_question')}
                  </label>
                  <div className="mt-2 space-y-2">
                    {features.map(feature => (
                      <div key={feature.value} className="flex items-center">
                        <input
                          id={feature.value}
                          type="checkbox"
                          name="features"
                          value={feature.value}
                          checked={selectedFeatures.includes(feature.value)}
                          onChange={handleFeatureChange}
                          className="h-4 w-4 text-blue-600 dark:text-blue-400 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
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
                    className="text-red-500 text-sm mt-1"
                  />
                </div>

                {/* Sugestie dotyczące ulepszenia wybranych funkcji */}
                {showImprovementSuggestions && (
                  <div>
                    <label htmlFor="featuresImprovement" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      {t('features_improvement_suggestions')}
                    </label>
                    <Textarea
                      id="featuresImprovement"
                      name="featuresImprovement"
                      className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-200"
                      rows={4}
                      placeholder={t('suggestion_placeholder')}
                    />
                    <ValidationError
                      prefix="Features Improvement"
                      field="featuresImprovement"
                      errors={state.errors}
                      className="text-red-500 text-sm mt-1"
                    />
                  </div>)
                }

                {/* Czy masz pomysł na nową funkcjonalność? */}
                <div>
                  <label htmlFor="newFeature" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('new_feature_question')}
                  </label>
                  <Textarea
                    id="newFeature"
                    name="newFeature"
                    className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-200"
                    rows={4}
                    placeholder={t('your_feedback')}
                  />
                  <ValidationError
                    prefix="New Feature"
                    field="newFeature"
                    errors={state.errors}
                    className="text-red-500 text-sm mt-1"
                  />
                </div>

                {/* Net Promoter Score (NPS) */}
                <div>
                  <label htmlFor="nps" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('nps_question')}
                  </label>
                  <select
                    id="nps"
                    name="nps"
                    className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-200"
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
                    className="text-red-500 text-sm mt-1"
                  />
                </div>

                {/* Łatwość Użytkowania */}
                <div>
                  <label htmlFor="usability" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('usability_question')}
                  </label>
                  <select
                    id="usability"
                    name="usability"
                    className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm p-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-200"
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
                    className="text-red-500 text-sm mt-1"
                  />
                </div>

                {/* Obsługa Błędów */}
                {hasErrors && (
                  <p className="text-red-500 text-sm text-center">
                    {t('form_error')}
                  </p>
                )}

                {/* Przycisk Submit */}
                <div className="mt-6">
                  <Button
                    type="submit"
                    disabled={state.submitting}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md transition duration-300"
                  >
                    {state.submitting ? t('sending') : t('submit')}
                  </Button>
                </div>
              </form>
            )}
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default FeedbackModal;
