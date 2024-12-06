// app/chat/[conversation_id]/page.tsx
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
      // If no conversation ID, redirect or handle the error
      router.push('/'); // Redirect to home or another page
    }
  }, [conversation_id, router]);

  if (!conversation_id) {
    return <div>Loading...</div>;
  }

  return <Chat userId={'user-123'} conversationId={Number(conversation_id)} />;
}
