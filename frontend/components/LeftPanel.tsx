'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { MessageSquare, BookOpen, ChevronLeft, ChevronRight, UserCircle, Settings, Plus, ChevronDown, ChevronUp } from 'lucide-react';
import Link from 'next/link';
import { LoginRegisterDialog } from "@/components/LoginRegisterDialog";
import { SettingsDialog } from "@/components/SettingsDialog";
import { useTheme } from 'next-themes';
import ManageFileDialog from '@/components/ManageFileDialog';
import { useTranslation } from 'react-i18next';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface Conversation {
  id: string;
  title: string;
  createdAt: string;
}

export function LeftPanel() {
  const [isPanelVisible, setIsPanelVisible] = useState(true);
  const [isHovered, setIsHovered] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { theme } = useTheme();
  const { t, i18n } = useTranslation();
  const [currentLanguage, setCurrentLanguage] = useState(i18n.language);

  useEffect(() => {
    const handleLanguageChange = () => setCurrentLanguage(i18n.language);
    i18n.on('languageChanged', handleLanguageChange);
    return () => i18n.off('languageChanged', handleLanguageChange);
  }, [i18n]);

  useEffect(() => {
    setConversations([
      { id: '1', title: t('conversation_1'), createdAt: '2024-12-01' },
      { id: '2', title: t('conversation_2'), createdAt: '2024-12-02' },
      { id: '3', title: t('conversation_3'), createdAt: '2024-12-03' },
    ]);
  }, [t]);

  const handleNewConversation = () => {
    console.log('Starting a new conversation');
  };

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(true), 200);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(false), 200);
  };

  const userId = 'user-123';

  return (
    <div
      className={`bg-card text-foreground border-r border-border transition-all duration-300 ${
        isPanelVisible ? 'w-64' : 'w-20'
      } flex flex-col`}
    >
      <div className="p-4 flex-grow">
        <h2 className={`text-xl font-semibold mb-4 ${isPanelVisible ? '' : 'sr-only'}`}>
          {t('menu')}
        </h2>
        <div className="space-y-4">
          <ManageFileDialog userId={userId} isPanelVisible={isPanelVisible} />

          <Button asChild variant="outline" className="w-full justify-start">
            <Link href="/flashcards">
              <BookOpen className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">{t('flashcards')}</span>}
            </Link>
          </Button>

          <div
            className="relative"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          >
            <Collapsible open={isHovered && isPanelVisible}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-start group hover:bg-secondary/80 transition-colors duration-200"
                >
                  <MessageSquare className="h-4 w-4" />
                  {isPanelVisible && (
                    <>
                      <span className="ml-2 flex-grow text-left">{t('chat')}</span>
                      {isHovered ? (
                        <ChevronUp className="h-4 w-4 transition-transform duration-200 ease-in-out" />
                      ) : (
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 ease-in-out" />
                      )}
                    </>
                  )}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 bg-secondary/50 rounded-md overflow-hidden shadow-lg">
                <div className="p-2 space-y-2">
                  <Button
                    className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full"
                    onClick={handleNewConversation}
                  >
                    <Plus className="h-4 w-4" />
                    {t('new_conversation')}
                  </Button>
                  {conversations.map((conv) => (
                    <Button
                      key={conv.id}
                      variant="ghost"
                      className="w-full justify-start text-sm hover:bg-secondary/80 transition-colors duration-200"
                    >
                      {conv.title}
                    </Button>
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-border">
        <div className="space-y-2">
          <LoginRegisterDialog>
            <Button variant="outline" className="w-full justify-start hover:bg-secondary/80 transition-colors duration-200">
              <UserCircle className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">{t('login_register')}</span>}
            </Button>
          </LoginRegisterDialog>
          <SettingsDialog>
            <Button variant="outline" className="w-full justify-start hover:bg-secondary/80 transition-colors duration-200">
              <Settings className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">{t('settings')}</span>}
            </Button>
          </SettingsDialog>
        </div>
      </div>

      <Button
        variant="ghost"
        className="self-end mb-4 mr-2 hover:bg-secondary/80 transition-colors duration-200"
        onClick={() => setIsPanelVisible(!isPanelVisible)}
        aria-label={isPanelVisible ? t('hide_panel') : t('show_panel')}
      >
        {isPanelVisible ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </Button>
    </div>
  );
}

