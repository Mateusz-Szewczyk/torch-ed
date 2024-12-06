// components/ClientLayout.tsx
'use client';

import React, { useState } from 'react';
import { LeftPanel } from '@/components/LeftPanel';
import Chat from '@/components/Chat';

interface ClientLayoutProps {
  children: React.ReactNode;
}

const ClientLayout: React.FC<ClientLayoutProps> = ({ children }) => {
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [isPanelVisible, setIsPanelVisible] = useState(true);
  const userId = 'user-123'; // Replace this with the actual user ID

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
