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
  const userId = 'user-123'; // Tutaj wstaw swój właściwy userId, jeśli to konieczne

  const pathname = usePathname();

  useEffect(() => {
    // Jeśli nie jesteśmy na stronie czatu, zresetuj currentConversationId
    if (!pathname.startsWith('/chat/')) {
      setCurrentConversationId(null);
    }
  }, [pathname]);

  return (
    <div className="flex h-screen bg-background text-foreground">
      <LeftPanel
        userId={userId}
        isPanelVisible={isPanelVisible}
        setIsPanelVisible={setIsPanelVisible}
        currentConversationId={currentConversationId}
        setCurrentConversationId={setCurrentConversationId}
      />
      <main className="flex-1 overflow-auto">
        {currentConversationId ? (
          <Chat userId={userId} conversationId={currentConversationId} />
        ) : (
          children
        )}
      </main>
    </div>
  );
};

export default ClientLayout;
