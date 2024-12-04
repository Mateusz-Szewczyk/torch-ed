import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import lokalizacji
import en from '@/locales/en.json';
import pl from '@/locales/pl.json';
import es from '@/locales/es.json';
import de from '@/locales/de.json';
import fr from '@/locales/fr.json';

const resources = {
  en: { translation: en },
  pl: { translation: pl },
  es: { translation: es },
  de: { translation: de },
  fr: { translation: fr },
};

i18n.use(initReactI18next).use(LanguageDetector) // Automatyczne wykrywanie języka
    .init({
      resources,
      lng: 'en',
      fallbackLng: 'en',
      interpolation: { escapeValue: false },
      react: { useSuspense: false },
});

export default i18n;
