// app/chat/page.tsx

'use client';

import React, { useContext, useEffect, useState } from 'react';
import Chat from '@/components/Chat';
import { ConversationContext } from '@/contexts/ConversationContext';

export default function ChatPage() {
  const { currentConversationId } = useContext(ConversationContext);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    console.log(`ChatPage: currentConversationId changed to: ${currentConversationId}`);
    if (currentConversationId !== null) {
      setIsLoading(false);
    }
  }, [currentConversationId]);

  if (isLoading) {
    return <div className="flex items-center justify-center h-full">Ładowanie konwersacji...</div>;
  }

  if (currentConversationId === null) {
    return <div className="flex items-center justify-center h-full">Wybierz konwersację z panelu bocznego.</div>;
  }

  return <Chat conversationId={currentConversationId} />;
}
