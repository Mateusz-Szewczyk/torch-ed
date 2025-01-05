'use client';

import React, { useState, useEffect } from 'react';
import { LeftPanel } from '@/components/LeftPanel';
import Chat from '@/components/Chat';
import { usePathname } from 'next/navigation';

interface ClientLayoutProps {
  children: React.ReactNode;
}

const ClientLayout: React.FC<ClientLayoutProps> = ({ children }) => {
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [isPanelVisible, setIsPanelVisible] = useState(true);

  // The critical piece: persistent login state
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const pathname = usePathname();

  // Check if user is on /chat/..., otherwise reset ID
  useEffect(() => {
    if (!pathname.startsWith('/chat/')) {
      setCurrentConversationId(null);
    }
  }, [pathname]);

  // On mount, check if user is still logged in'''
  useEffect(() => {
    const checkSession = async () => {
      try {
        const res = await fetch('http://localhost:14440/api/v1/auth/me', {
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

  return (
    <div className="flex h-screen bg-background text-foreground">
      <LeftPanel
        isAuthenticated={isAuthenticated}
        setIsAuthenticated={setIsAuthenticated}
        isPanelVisible={isPanelVisible}
        setIsPanelVisible={setIsPanelVisible}
        currentConversationId={currentConversationId}
        setCurrentConversationId={setCurrentConversationId}
      />
      <main className="flex-1 overflow-auto">
        {currentConversationId ? <Chat conversationId={currentConversationId} /> : children}
      </main>
    </div>
  );
};

export default ClientLayout;
