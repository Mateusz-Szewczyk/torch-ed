// next-i18next.config.js

module.exports = {
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'pl', 'es', 'fr', 'de'], // Dodaj więcej języków w razie potrzeby
  },
  react: { useSuspense: false }, // Ważne dla SSR
};
