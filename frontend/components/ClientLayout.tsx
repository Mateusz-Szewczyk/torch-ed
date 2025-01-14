// src/components/ClientLayout.tsx

'use client';

import React, { useState, useEffect } from 'react';
import LeftPanel from '@/components/LeftPanel';
import Chat from '@/components/Chat';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ClientLayoutProps {
  children: React.ReactNode;
}

const ClientLayout: React.FC<ClientLayoutProps> = ({ children }) => {
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [isPanelVisible, setIsPanelVisible] = useState<boolean>(true);
  const [isMobile, setIsMobile] = useState<boolean>(false);

  const pathname = usePathname();

  // Reset currentConversationId when navigating away from /chat/
  useEffect(() => {
    if (!pathname.startsWith('/chat/')) {
      setCurrentConversationId(null);
    }
  }, [pathname]);

  // Sprawdzanie, czy użytkownik korzysta z urządzenia mobilnego
  useEffect(() => {
    const checkMobile = () => {
      const isNowMobile = window.innerWidth < 768;
      setIsMobile(isNowMobile);
      setIsPanelVisible(!isNowMobile);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Dodawanie lub usuwanie klasy do body w zależności od widoczności panelu na urządzeniach mobilnych
  useEffect(() => {
    if (isMobile && isPanelVisible) {
      document.body.classList.add('mobile-menu-open');
    } else {
      document.body.classList.remove('mobile-menu-open');
    }
  }, [isMobile, isPanelVisible]);

  // Funkcja do przełączania widoczności panelu
  const togglePanel = () => {
    setIsPanelVisible(!isPanelVisible);
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <LeftPanel/>
      <main
        className={`flex-1 overflow-auto transition-all duration-300 ${
          isMobile
            ? 'w-full'
            : isPanelVisible
              ? 'ml-64 w-[calc(100%-16rem)]'
              : 'ml-16 w-[calc(100%-4rem)]'
        }`}
      >
        {isMobile && isPanelVisible && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-40"
            onClick={() => setIsPanelVisible(false)}
          />
        )}
        {currentConversationId ? <Chat conversationId={currentConversationId} /> : children}
      </main>
      {isMobile && !isPanelVisible && (
        <Button
          variant="ghost"
          className="fixed top-1/2 left-0 z-40 transform -translate-y-1/2 bg-card hover:bg-secondary/80 transition-colors duration-200 rounded-r-full w-8 h-16 flex items-center justify-center"
          onClick={togglePanel}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
};

export default ClientLayout;
