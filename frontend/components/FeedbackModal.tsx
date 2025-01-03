// components/FeedbackModal.tsx

'use client';

import React, { useState, useEffect } from 'react';
import { useForm, ValidationError } from '@formspree/react';
import { useTranslation } from 'react-i18next';

type FeedbackModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

const FeedbackModal: React.FC<FeedbackModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const [state, handleSubmit] = useForm("xvgojkjv"); // Zastąp "xvgojkjv" swoim rzeczywistym Formspree form ID
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
    { value: 'Flashcards generations', label: t('features_list.Flashcard Generation') },
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-8 w-full max-w-md relative overflow-y-auto max-h-full">
        <button
          onClick={onClose}
          className="absolute top-2 right-2 text-gray-500 hover:text-gray-700 text-2xl font-bold"
          aria-label="Close Feedback Form"
        >
          &times;
        </button>
        {state.succeeded ? (
          <p className="text-green-500 text-center">{t('feedback_thanks')}</p>
        ) : (
          <>
            <h2 className="text-2xl font-bold mb-4 text-center">{t('send_feedback')}</h2>
            <p className="text-center mb-4">{t('feedback_description')}</p>
            <form onSubmit={handleSubmit} className="space-y-4">

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
                  <option value="1">1 - Bardzo niezadowolony</option>
                  <option value="2">2 - Niezadowolony</option>
                  <option value="3">3 - Neutralny</option>
                  <option value="4">4 - Zadowolony</option>
                  <option value="5">5 - Bardzo zadowolony</option>
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
                  <textarea
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
                <textarea
                  id="newFeature"
                  name="newFeature"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
                  rows={4}
                />
                <ValidationError
                  prefix="New Feature"
                  field="newFeature"
                  errors={state.errors}
                />
              </div>

              {/* Dodatkowe Pytania */}
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
                  <option value="0">0</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                  <option value="4">4</option>
                  <option value="5">5</option>
                  <option value="6">6</option>
                  <option value="7">7</option>
                  <option value="8">8</option>
                  <option value="9">9</option>
                  <option value="10">10</option>
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
                  <option value="1">1 - Bardzo trudne</option>
                  <option value="2">2 - Trudne</option>
                  <option value="3">3 - Neutralne</option>
                  <option value="4">4 - Łatwe</option>
                  <option value="5">5 - Bardzo łatwe</option>
                </select>
                <ValidationError
                  prefix="Usability"
                  field="usability"
                  errors={state.errors}
                />
              </div>

              {/* Obsługa Błędów */}
              {(state.errors?.length || 0) > 0 && (
                <p className="text-red-500 text-sm">{t('form_error')}</p>
              )}

              {/* Przycisk Submit */}
              <button
                type="submit"
                disabled={state.submitting}
                className="w-full bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors duration-300"
              >
                {state.submitting ? t('sending') : t('submit')}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default FeedbackModal;
