// components/ClientLayout.tsx
'use client';

import React, { useState } from 'react';
import { LeftPanel } from '@/components/LeftPanel';
import Chat from '@/components/Chat';

const ClientLayout: React.FC = ({ children }) => {
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [isPanelVisible, setIsPanelVisible] = useState(true);
  const userId = 'user-123'; // Zastąp to rzeczywistym ID użytkownika

  return (
    <div className="flex h-screen bg-background text-foreground">
      <LeftPanel
        userId={userId}
        isPanelVisible={isPanelVisible}
        setIsPanelVisible={setIsPanelVisible}
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
