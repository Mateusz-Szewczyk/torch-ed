// app/chat/page.tsx

'use client';

import { useParams, useRouter } from 'next/navigation';
import Chat from '@/components/Chat';
import { useEffect } from 'react';

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const { conversation_id } = params;

  useEffect(() => {
    if (!conversation_id) {
      // Jeśli nie ma conversation ID, przekieruj lub obsłuż błąd
      router.push('/'); // Przekierowanie do strony głównej lub innej strony
    }
  }, [conversation_id, router]);

  if (!conversation_id) {
    return <div>Loading...</div>;
  }

  return <Chat conversationId={Number(conversation_id)} />;
}