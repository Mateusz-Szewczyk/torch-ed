'use client';

import React, { useState, useEffect } from 'react';
import { LeftPanel } from '@/components/LeftPanel';
import Chat from '@/components/Chat';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ClientLayoutProps {
  children: React.ReactNode;
}

const ClientLayout: React.FC<ClientLayoutProps> = ({ children }) => {
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [isPanelVisible, setIsPanelVisible] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const pathname = usePathname();

  useEffect(() => {
    if (!pathname.startsWith('/chat/')) {
      setCurrentConversationId(null);
    }
  }, [pathname]);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_FLASK_URL || 'http://localhost:14440/api/v1';
        const res = await fetch(`${API_BASE_URL}/auth/me`, {
          credentials: 'include',
        });
        if (res.ok) {
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
        }
      } catch (err) {
        console.error('Error verifying session:', err);
        setIsAuthenticated(false);
      }
    };

    checkSession();
  }, []);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      setIsPanelVisible(window.innerWidth >= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (isMobile && isPanelVisible) {
      document.body.classList.add('mobile-menu-open');
    } else {
      document.body.classList.remove('mobile-menu-open');
    }
  }, [isMobile, isPanelVisible]);

  const togglePanel = () => {
    setIsPanelVisible(!isPanelVisible);
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <LeftPanel
        isAuthenticated={isAuthenticated}
        setIsAuthenticated={setIsAuthenticated}
        isPanelVisible={isPanelVisible}
        setIsPanelVisible={setIsPanelVisible}
        currentConversationId={currentConversationId}
        setCurrentConversationId={setCurrentConversationId}
      />
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
