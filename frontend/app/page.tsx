'use client';

import { useTranslation, Trans } from 'react-i18next';
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  CardContent
} from "@/components/ui/card";

import {
  Sparkles,
  Cpu,
  Wand2,
  LayoutDashboard
} from 'lucide-react';

// Import ikon z react-icons
import { FaGithub, FaLinkedin, FaRegLightbulb } from 'react-icons/fa'; // Dodana ikona FaRegLightbulb

// Definicja typu dla planów
interface FuturePlan {
  title: string;
  description: string;
}

export default function HomePage() {
  const { t } = useTranslation();

  // Przykładowe sekcje do kart
  const sections = [
    {
      icon: Sparkles,
      title: t('homepage_modern_section_title1'),
      description: t('homepage_modern_section_text1'),
    },
    {
      icon: Cpu,
      title: t('homepage_modern_section_title2'),
      description: t('homepage_modern_section_text2'),
    },
    {
      icon: Wand2,
      title: t('homepage_modern_section_title3'),
      description: t('homepage_modern_section_text3'),
    },
  ];

  const highlights = [
    t('homepage_modern_highlight1'),
    t('homepage_modern_highlight2'),
    t('homepage_modern_highlight3'),
  ];

  // Pobieranie planów jako tablicy obiektów
  const futurePlans: FuturePlan[] = t('future_plans.items', { returnObjects: true }) as FuturePlan[];

  // Debugging: Sprawdzenie zawartości futurePlans
  console.log('Future Plans:', futurePlans);

  return (
    <div className="relative flex flex-col min-h-screen bg-gradient-to-br from-[hsl(var(--background))] to-[hsl(var(--border))] text-[hsl(var(--foreground))]">

      {/* Bąbelki w tle - pozycjonowanie, żeby były widoczne */}
      <div className="absolute inset-0 -z-1 overflow-hidden">
        {/* Każdy bąbelek ma top/left określone inline, + klasa animująca */}
        <div
          className="absolute w-72 h-72 bg-pink-300/50 rounded-full animate-randomBallOne"
          style={{ top: '20%', left: '10%' }}
        />
        <div
          className="absolute w-80 h-80 bg-blue-300/50 rounded-full animate-randomBallTwo"
          style={{ top: '50%', left: '60%' }}
        />
        <div
          className="absolute w-96 h-96 bg-green-300/40 rounded-full animate-randomBallThree"
          style={{ top: '10%', left: '70%' }}
        />
        <div
          className="absolute w-64 h-64 bg-purple-300/40 rounded-full animate-randomBallFour"
          style={{ top: '70%', left: '20%' }}
        />
      </div>

      {/* Hero / Intro */}
      <section className="py-20 px-4 flex flex-col items-center text-center z-10">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Użycie komponentu Trans do wstawienia animowanego słowa */}
          <h1 className="text-6xl font-extrabold drop-shadow-md">
            <Trans i18nKey="modern_homepage_title">
              Tutaj zaczyna i kończy się Twoja nauka
            </Trans>
          </h1>
          <p className="text-xl text-muted-foreground">
            {t('modern_homepage_subtitle')}
          </p>
          <p className="text-lg text-foreground animate-fadeIn">
            {t('modern_homepage_intro_text')}
          </p>
        </div>
      </section>

      {/* Sekcja Feature Cards */}
      <section className="py-16 px-4">
        <div className="container mx-auto grid md:grid-cols-3 gap-8">
          {sections.map((sec, idx) => (
            <Card
              key={idx}
              className="bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]
                         transform hover:-translate-y-2 hover:shadow-2xl
                         transition-all duration-500 animate-fadeInUp"
            >
              <CardHeader className="flex items-center space-x-3">
                <sec.icon className="h-8 w-8 text-[hsl(var(--primary))]" />
                <CardTitle className="text-xl">{sec.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-foreground/90 text-sm mt-4">
                  {sec.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Sekcja Highlights */}
      <section className="px-4 py-16 bg-[hsl(var(--background))]/80 z-5 shadow-custom">
        <div className="container mx-auto text-center space-y-8">
          <h2 className="text-4xl font-bold">{t('modern_homepage_highlights_title')}</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            {t('modern_homepage_highlights_subtitle')}
          </p>
          <ul className="mt-10 space-y-6 max-w-lg mx-auto text-left animate-fadeIn">
            {highlights.map((hl, i) => (
              <li key={i} className="flex space-x-2 items-start">
                <LayoutDashboard className="mt-1 text-[hsl(var(--primary))]" />
                <span className="text-lg">{hl}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Sekcja Plany na Przyszłość */}
      <section className="py-16 px-4 text-[hsl(var(--card-foreground))]">
        <div className="container mx-auto text-center space-y-8">
          {/* Nagłówek z ikoną */}
          <div className="flex justify-center items-center space-x-4">
            <FaRegLightbulb className="h-8 w-8 text-[hsl(var(--primary))]" />
            <h2 className="text-4xl font-bold">{t('future_plans.title')}</h2>
          </div>
          {/* Opis sekcji z dodatkowym paddingiem */}
          <p className="text-muted-foreground max-w-2xl mx-auto px-4">
            {t('future_plans.description')}
          </p>
          {/* Karty z planami */}
          <div className="mt-10 grid sm:grid-cols-1 md:grid-cols-2 gap-8">
            {futurePlans.map((plan, index) => (
              <Card
                key={index}
                className="bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]
                           p-8 rounded-lg shadow-md transform hover:scale-105
                           transition-transform duration-300"
              >
                <CardTitle className="text-xl font-semibold mb-2">
                  {plan.title}
                </CardTitle>
                <CardDescription className="text-sm text-muted-foreground">
                  {plan.description}
                </CardDescription>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Stopka */}
      <footer className="bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))] py-6 mt-auto">
        <div className="container mx-auto px-4 flex flex-col md:flex-row items-center justify-between">
          <p className="text-sm">
            &copy; {new Date().getFullYear()} Mateusz Szewczyk &amp; Adam Sarga. {t('all_rights_reserved')}
          </p>
          <div className="flex space-x-4 mt-4 md:mt-0">
            {/* GitHub - Mateusz */}
            <a
              href="https://github.com/Mateusz-Szewczyk"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[hsl(var(--primary))] transition-colors duration-200"
              aria-label="GitHub Mateusz Szewczyk"
            >
              <FaGithub className="h-6 w-6" />
            </a>

            {/* LinkedIn - Mateusz */}
            <a
              href="https://www.linkedin.com/in/mateusz-szewczyk-09073220b/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[hsl(var(--primary))] transition-colors duration-200"
              aria-label="LinkedIn Mateusz Szewczyk"
            >
              <FaLinkedin className="h-6 w-6" />
            </a>

            {/* GitHub - Adam */}
            <a
              href="https://github.com/Vronst"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[hsl(var(--primary))] transition-colors duration-200"
              aria-label="GitHub Adam Sarga"
            >
              <FaGithub className="h-6 w-6" />
            </a>

            {/* LinkedIn - Adam */}
            <a
              href="https://www.linkedin.com/in/adam-sarga-613863272/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[hsl(var(--primary))] transition-colors duration-200"
              aria-label="LinkedIn Adam Sarga"
            >
              <FaLinkedin className="h-6 w-6" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
