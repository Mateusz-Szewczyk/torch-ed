// src/components/ClientLayout.tsx

'use client';

import React, { useState, useEffect } from 'react';
import LeftPanel from '@/components/left-panel/index';
import Chat from '@/components/Chat';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTranslation } from 'react-i18next';

interface ClientLayoutProps {
  children: React.ReactNode;
}

const ClientLayout: React.FC<ClientLayoutProps> = ({ children }) => {
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [isPanelVisible, setIsPanelVisible] = useState<boolean>(true);
  const [isMobile, setIsMobile] = useState<boolean>(false);

  const pathname = usePathname();
  const { t } = useTranslation();

  // Reset currentConversationId when navigating away from /chat/
  useEffect(() => {
    if (!pathname.startsWith('/chat/')) {
      setCurrentConversationId(null);
    }
  }, [pathname]);

  // Check if device is mobile
  useEffect(() => {
    const checkMobile = () => {
      const isNowMobile = window.innerWidth < 768;
      setIsMobile(isNowMobile);
      setIsPanelVisible(!isNowMobile); // Show panel on desktop, hide on mobile by default
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Add or remove class to body based on panel visibility on mobile
  useEffect(() => {
    if (isMobile && isPanelVisible) {
      document.body.classList.add('mobile-menu-open');
    } else {
      document.body.classList.remove('mobile-menu-open');
    }
  }, [isMobile, isPanelVisible]);

  // Function to toggle panel visibility
  const togglePanel = () => {
    setIsPanelVisible(!isPanelVisible);
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Render LeftPanel with props */}
      <LeftPanel isPanelVisible={isPanelVisible} isMobile={isMobile} togglePanel={togglePanel} />

      <main
        className={`flex-1 overflow-auto transition-all duration-300 ${
          isMobile
            ? 'w-full'
            : isPanelVisible
              ? 'ml-64 w-[calc(100%-16rem)]'
              : 'ml-16 w-[calc(100%-4rem)]'
        }`}
      >
        {/* Overlay for mobile when panel is open */}
        {isMobile && isPanelVisible && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-40"
            onClick={() => setIsPanelVisible(false)}
          />
        )}

        {/* Render Chat or children */}
        {currentConversationId ? <Chat conversationId={currentConversationId} /> : children}
      </main>

      {/* Button to open panel on mobile when panel is hidden */}
      {isMobile && !isPanelVisible && (
        <Button
          variant="ghost"
          className="fixed top-1/2 left-0 z-50 transform -translate-y-1/2 bg-card hover:bg-secondary/80 transition-colors duration-200 rounded-r-full w-8 h-16 flex items-center justify-center"
          onClick={togglePanel}
          aria-label={t('open_menu') || 'Open Menu'}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
};

export default ClientLayout;
