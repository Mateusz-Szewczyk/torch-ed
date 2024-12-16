// components/HomePage.tsx

'use client';

import { useTranslation } from 'react-i18next';
import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { BookOpen, MessageSquare, Bell, ArrowRight} from 'lucide-react';
import FeedbackModal from '@/components/FeedbackModal'; // Importuj FeedbackModal

export default function HomePage() {
  const { t } = useTranslation();
  const router = useRouter();

  const examplePrompts = [
    t('example_prompt_1'),
    t('example_prompt_2'),
    t('example_prompt_3'),
  ];

  const newsItems = [
    { title: t('news_item_1_title'), description: t('news_item_1_description') },
    { title: t('news_item_2_title'), description: t('news_item_2_description') },
    { title: t('news_item_3_title'), description: t('news_item_3_description') },
  ];

  return (
    <div
      className="min-h-screen bg-[radial-gradient(ellipse_farthest-corner_at_top,_hsl(var(--border)),_hsl(var(--background)),_hsl(var(--border)))] text-[hsl(var(--foreground))] relative overflow-hidden"
    >
      {/* Hero Section */}
      <section className="py-20 px-4 text-center relative z-10">
        <div className="container mx-auto flex flex-col items-center justify-center">
          <div className="mb-8">
            <h1 className="text-5xl font-extrabold mb-4">{t('welcome_title')}</h1>
            <p className="text-xl mb-8">{t('welcome_subtitle')}</p>
            <div className="flex space-x-4 justify-center">
              <Button
                onClick={() => router.push('/flashcards')}
                size="lg"
                className="flex items-center bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:bg-[hsl(var(--primary))] transition-colors duration-300 animate-pulseButton mx-auto"
              >
                {t('get_started')}
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>
      </section>

      <div className="container mx-auto px-4 py-16 space-y-20 relative z-10">
        {/* Purpose Section */}
        <section>
          <h2 className="text-4xl font-bold mb-12 text-center">{t('purpose_title')}</h2>
          <div className="grid md:grid-cols-3 gap-12">
            <Card
              className="transform transition-transform duration-300 hover:scale-105 hover:-translate-y-2 hover:shadow-lg bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]"
            >
              <CardHeader className="flex items-center">
                <BookOpen className="h-8 w-8 text-[hsl(var(--primary))] mr-4" />
                <CardTitle className="text-xl">{t('purpose_feature_1_title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{t('purpose_feature_1_description')}</p>
              </CardContent>
            </Card>
            <Card
              className="transform transition-transform duration-300 hover:scale-105 hover:-translate-y-2 hover:shadow-lg bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]"
            >
              <CardHeader className="flex items-center">
                <MessageSquare className="h-8 w-8 text-[hsl(var(--primary))] mr-4" />
                <CardTitle className="text-xl">{t('purpose_feature_2_title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{t('purpose_feature_2_description')}</p>
              </CardContent>
            </Card>
            <Card
              className="transform transition-transform duration-300 hover:scale-105 hover:-translate-y-2 hover:shadow-lg bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]"
            >
              <CardHeader className="flex items-center">
                <Bell className="h-8 w-8 text-[hsl(var(--primary))] mr-4" />
                <CardTitle className="text-xl">{t('purpose_feature_3_title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{t('purpose_feature_3_description')}</p>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Example Prompts Section */}
        <section>
          <h2 className="text-4xl font-bold mb-12 text-center">{t('example_prompts_title')}</h2>
          <div className="bg-[hsl(var(--card))] shadow-md rounded-lg p-8">
            <ul className="space-y-6">
              {examplePrompts.map((prompt, index) => (
                <li key={index} className="flex items-start">
                  <span className="font-bold text-[hsl(var(--primary))] mr-4 text-lg">{index + 1}.</span>
                  <span className="text-[hsl(var(--foreground))]">{prompt}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* News Section */}
        <section>
          <h2 className="text-4xl font-bold mb-12 text-center">{t('news_title')}</h2>
          <div className="grid md:grid-cols-3 gap-12">
            {newsItems.map((item, index) => (
              <Card key={index}
                className="transform transition-transform duration-300 hover:scale-105 hover:-translate-y-2 hover:shadow-lg bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]"
              >
                <CardHeader className="flex items-center">
                  <MessageSquare className="h-8 w-8 text-[hsl(var(--primary))] mr-4" />
                  <CardTitle className="text-xl">{item.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-[hsl(var(--foreground))]">{item.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))] py-6 relative z-10">
        <div className="container mx-auto px-4 flex flex-col md:flex-row items-center justify-between">
          <p className="text-sm">&copy; {new Date().getFullYear()} Mateusz Szewczyk. All rights reserved.</p>
          <div className="flex space-x-4 mt-4 md:mt-0">
            <a href="https://github.com/Mateusz-Szewczyk" target="_blank" rel="noopener noreferrer"
              className="hover:text-[hsl(var(--primary))] transition-colors duration-200">
              {/* GitHub Icon */}
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                {/* GitHub Path */}
                <path
                  d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
            </a>
            <a href="https://www.linkedin.com/in/mateusz-szewczyk-09073220b/" target="_blank"
              rel="noopener noreferrer" className="hover:text-[hsl(var(--primary))] transition-colors duration-200">
              {/* LinkedIn Icon */}
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                {/* LinkedIn Path */}
                <path
                  d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.784 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
              </svg>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
