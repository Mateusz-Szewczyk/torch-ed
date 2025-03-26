// src/app/page.tsx

'use client';

import { useTranslation, Trans } from 'react-i18next';
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  CardContent
} from "@/components/ui/card";

import { MdErrorOutline } from 'react-icons/md';

import {
  Sparkles,
  Cpu,
  Wand2,
  LayoutDashboard
} from 'lucide-react';

import { FaGithub, FaLinkedin, FaRegLightbulb } from 'react-icons/fa';

import Dashboard from '@/components/Dashboard';

import { useContext, useEffect, useState } from 'react';
import { AuthContext } from '@/contexts/AuthContext';

interface FuturePlan {
  title: string;
  description: string;
}

export default function HomePage() {
  const { t } = useTranslation();
  const { isAuthenticated, accessDenied, setAccessDenied, setTokenExpired, tokenExpired } = useContext(AuthContext);

  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (accessDenied) {
      timer = setTimeout(() => {
        setFadeOut(true);
      }, 4500);
      const resetTimer = setTimeout(() => {
        setAccessDenied(false);
        setFadeOut(false);
      }, 8000);
      return () => {
        clearTimeout(timer);
        clearTimeout(resetTimer);
      };
    }
  }, [accessDenied, setAccessDenied]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (tokenExpired) {
      timer = setTimeout(() => {
        setFadeOut(true);
      }, 4500);
      const resetTimer = setTimeout(() => {
        setTokenExpired(false);
        setFadeOut(false);
      }, 8000);
      return () => {
        clearTimeout(timer);
        clearTimeout(resetTimer);
      };
    }
  }, [tokenExpired, setTokenExpired]);

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

  const rawFuturePlans = t('future_plans.items', { returnObjects: true });

  let futurePlans: FuturePlan[] = [];
  if (Array.isArray(rawFuturePlans)) {
    futurePlans = rawFuturePlans as FuturePlan[];
  } else {
    console.warn('future_plans.items is not an array:', rawFuturePlans);
  }

  const content = isAuthenticated ? (
    <Dashboard />
  ) : (
    <div
      className="relative flex flex-col max-w-[100%] mx-auto min-h-screen bg-gradient-to-br from-[hsl(var(--background))] to-[hsl(var(--border))] text-[hsl(var(--foreground))] overflow-x-hidden"
    >
      {/* Bąbelki w tle */}
      <div className="absolute bubbleOne" />
      <div className="absolute bubbleTwo" />
      <div className="absolute bubbleThree" />
      <div className="absolute bubbleFour" />

      {/* Hero / Intro */}
      <section className="py-20 px-4 flex flex-col items-center text-center z-10">
        <div className="max-w-3xl mx-auto space-y-6">
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold drop-shadow-md">
            <Trans i18nKey="modern_homepage_title">
              Tutaj zaczyna i kończy się Twoja nauka
            </Trans>
          </h1>
          <p className="text-base sm:text-lg md:text-xl text-muted-foreground">
            {t('modern_homepage_subtitle')}
          </p>
          <p className="text-base sm:text-lg md:text-xl text-foreground animate-fadeIn">
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
              className="bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))] transform hover:-translate-y-2 hover:shadow-2xl transition-all duration-500 animate-fadeInUp"
            >
              <CardHeader className="flex items-center space-x-3 animate-textGradient">
                <sec.icon className="h-8 w-8 text-[hsl(var(--primary))]" />
                <CardTitle className="text-lg sm:text-xl md:text-xl">{sec.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-foreground/90 text-xs sm:text-sm md:text-sm mt-4">
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
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold">
            {t('modern_homepage_highlights_title')}
          </h2>
          <p className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
            {t('modern_homepage_highlights_subtitle')}
          </p>
          <ul className="mt-10 space-y-6 max-w-lg mx-auto text-left animate-fadeIn">
            {highlights.map((hl, i) => (
              <li key={i} className="flex space-x-2 items-start">
                <LayoutDashboard className="mt-1 text-[hsl(var(--primary))] h-6 w-6" />
                <span className="text-base sm:text-lg md:text-lg">{hl}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Sekcja Plany na Przyszłość */}
      <section className="py-16 px-4 text-[hsl(var(--card-foreground))]">
        <div className="container mx-auto text-center space-y-8">
          <div className="flex justify-center items-center space-x-4">
            <FaRegLightbulb className="h-8 w-8 text-[hsl(var(--primary))]" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold">
              {t('future_plans.title')}
            </h2>
          </div>
          <p className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto px-4">
            {t('future_plans.description')}
          </p>
          <div className="mt-10 grid sm:grid-cols-1 md:grid-cols-2 gap-8">
            {futurePlans.map((plan, index) => (
              <Card
                key={index}
                className="bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))] p-8 rounded-lg shadow-md transform hover:scale-105 transition-transform duration-300 text-base sm:text-lg md:text-base"
              >
                <CardTitle className="text-lg sm:text-xl font-semibold mb-2">
                  {plan.title}
                </CardTitle>
                <CardDescription className="text-xs sm:text-sm text-muted-foreground">
                  {plan.description}
                </CardDescription>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Stopka */}
      <footer className="z-10 bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))] py-6 mt-auto">
        <div className="container mx-auto px-4 flex flex-col md:flex-row items-center justify-between">
          <p className="text-xs sm:text-sm">
            &copy; {new Date().getFullYear()} Mateusz Szewczyk &amp; Adam Sarga. {t('all_rights_reserved')}
          </p>
          <div className="flex space-x-4 mt-4 md:mt-0">
            <a
              href="https://github.com/Mateusz-Szewczyk"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[hsl(var(--primary))] transition-colors duration-200"
              aria-label="GitHub Mateusz Szewczyk"
            >
              <FaGithub className="h-6 w-6" />
            </a>
            <a
              href="https://www.linkedin.com/in/mateusz-szewczyk-09073220b/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[hsl(var(--primary))] transition-colors duration-200"
              aria-label="LinkedIn Mateusz Szewczyk"
            >
              <FaLinkedin className="h-6 w-6" />
            </a>
            <a
              href="https://github.com/Vronst"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[hsl(var(--primary))] transition-colors duration-200"
              aria-label="GitHub Adam Sarga"
            >
              <FaGithub className="h-6 w-6" />
            </a>
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

  return (
    <>
      {content}
      {accessDenied && (
        <div
          className={`fixed bottom-5 left-1/2 transform -translate-x-1/2 flex items-center bg-red-600 bg-opacity-90 backdrop-blur-md text-white py-3 px-6 rounded-xl shadow-lg z-50 transition-all duration-500 ${
            fadeOut ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'
          }`}
        >
          <MdErrorOutline className="mr-2 text-xl" />
          <p className="text-sm font-medium">
            Niestety nie masz dostępu do tego zasobu, spróbuj zalogować/zarejestrować się i spróbuj ponownie.
          </p>
        </div>
      )}
      {tokenExpired && (
        <div
          className={`fixed bottom-5 left-1/2 transform -translate-x-1/2 flex items-center bg-red-600 bg-opacity-90 backdrop-blur-md text-white py-3 px-6 rounded-xl shadow-lg z-50 transition-all duration-500 ${
            fadeOut ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'
          }`}
        >
          <MdErrorOutline className="mr-2 text-xl" />
          <p className="text-sm font-medium">
            Z powodu nieaktywności zostałeś wylogowany. Zaloguj się ponownie aby kontynuować
          </p>
        </div>
      )}
    </>
  );
}
