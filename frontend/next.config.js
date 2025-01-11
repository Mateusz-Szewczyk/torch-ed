// next.config.js

const { i18n } = ('./next-i18next.config');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  i18n,
  // Inne opcje konfiguracji
};

module.exports = nextConfig;
