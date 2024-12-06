// components/HomePage.tsx
'use client';

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { BookOpen, MessageSquare, Bell, ArrowRight } from 'lucide-react';

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
      </section>

      <div className="container mx-auto px-4 py-16 space-y-20 relative z-10">
        {/* Purpose Section */}
        <section>
          <h2 className="text-4xl font-bold mb-12 text-center">{t('purpose_title')}</h2>
          <div className="grid md:grid-cols-3 gap-12">
            <Card className="transform transition-transform duration-300 hover:scale-105 hover:-translate-y-2 hover:shadow-lg bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]">
              <CardHeader className="flex items-center">
                <BookOpen className="h-8 w-8 text-[hsl(var(--primary))] mr-4" />
                <CardTitle className="text-xl">{t('purpose_feature_1_title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{t('purpose_feature_1_description')}</p>
              </CardContent>
            </Card>
            <Card className="transform transition-transform duration-300 hover:scale-105 hover:-translate-y-2 hover:shadow-lg bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]">
              <CardHeader className="flex items-center">
                <MessageSquare className="h-8 w-8 text-[hsl(var(--primary))] mr-4" />
                <CardTitle className="text-xl">{t('purpose_feature_2_title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{t('purpose_feature_2_description')}</p>
              </CardContent>
            </Card>
            <Card className="transform transition-transform duration-300 hover:scale-105 hover:-translate-y-2 hover:shadow-lg bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]">
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
              <Card key={index} className="transform transition-transform duration-300 hover:scale-105 hover:-translate-y-2 hover:shadow-lg bg-[hsl(var(--card))] text-[hsl(var(--card-foreground))]">
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
            <a href="https://github.com/yourprofile" target="_blank" rel="noopener noreferrer" className="hover:text-[hsl(var(--primary))] transition-colors duration-200">
              {/* GitHub Icon */}
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                {/* GitHub Path */}
                <path d="M12 0C5.371 0 0 5.373 0 12c0 5.303..."/>
              </svg>
            </a>
            <a href="https://twitter.com/yourprofile" target="_blank" rel="noopener noreferrer" className="hover:text-[hsl(var(--primary))] transition-colors duration-200">
              {/* Twitter Icon */}
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                {/* Twitter Path */}
                <path d="M24 4.557a9.83 9.83 0 01-2.828.775..."/>
              </svg>
            </a>
            <a href="https://linkedin.com/in/yourprofile" target="_blank" rel="noopener noreferrer" className="hover:text-[hsl(var(--primary))] transition-colors duration-200">
              {/* LinkedIn Icon */}
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                {/* LinkedIn Path */}
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0..."/>
              </svg>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
