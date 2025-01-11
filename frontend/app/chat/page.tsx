// app/chat/page.tsx

'use client';

import Chat from '@/components/Chat';
import { useContext } from 'react';
import { ConversationContext } from '@/contexts/ConversationContext';

export default function ChatPage() {
  const { currentConversationId } = useContext(ConversationContext);

  if (!currentConversationId) {
    return <div>Wybierz konwersację z panelu bocznego.</div>;
  }

  return <Chat conversationId={currentConversationId} />;
}
