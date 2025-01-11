import React, { useState, useEffect, useRef } from 'react';
import { SendIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Message = {
  id: number;
  conversation_id: number;
  text: string;
  sender: 'user' | 'bot';
  created_at: string;
  isNew?: boolean;
  isError?: boolean;
};

interface ChatProps {
  conversationId: number;
}

const Chat: React.FC<ChatProps> = ({ conversationId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';

  // Autoscroll
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Fetch messages
  const fetchMessages = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        method: 'GET',
      });
      if (res.ok) {
        const data: Message[] = await res.json();
        setMessages(data.map(msg => ({ ...msg, isNew: false, isError: false })));
      } else {
        console.error('Failed to fetch messages:', res.statusText);
      }
    } catch (err) {
      console.error('Error fetching messages:', err);
    }
  };

  useEffect(() => {
    if (conversationId) fetchMessages();
  }, [conversationId]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userInput = input.trim();
    setInput('');

    const userMsg: Message = {
      id: Date.now(),
      conversation_id: conversationId,
      text: userInput,
      sender: 'user',
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      setIsLoading(true);
      setError('');

      // Save user message
      const userMessageResponse = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: 'user', text: userInput }),
      });

      if (!userMessageResponse.ok) {
        const errData = await userMessageResponse.json();
        throw new Error(errData.detail || 'Error sending user message.');
      }

      // Query endpoint
      const response = await fetch(`${API_BASE_URL}/query/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          query: userInput,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || `Error: ${response.statusText}`);
      }

      const data = await response.json();

      const botMsg: Message = {
        id: Date.now() + 1,
        conversation_id: conversationId,
        text: data.answer,
        sender: 'bot',
        created_at: new Date().toISOString(),
      };

      // Save bot message
      const botMessageResponse = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: 'bot', text: data.answer }),
      });

      if (!botMessageResponse.ok) {
        const errData = await botMessageResponse.json();
        throw new Error(errData.detail || 'Error sending bot message.');
      }

      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      console.error('Error sending message:', err);
      const errorText = err instanceof Error ? err.message : String(err);

      const errorMessage: Message = {
        id: Date.now() + 2,
        conversation_id: conversationId,
        text: errorText,
        sender: 'bot',
        created_at: new Date().toISOString(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
      setError(errorText);
    } finally {
      setIsLoading(false);
    }
  };

  const MessageBubble = ({ message }: { message: Message }) => {
    const isUser = message.sender === 'user';

    return (
      <div className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`
          relative 
          ${isUser ? 'ml-12' : 'mr-12'} 
          max-w-[80%] 
          p-4
          rounded-2xl
          ${isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'}
          ${message.isError ? 'border-2 border-destructive' : ''}
          shadow-sm
        `}>
          <div className="prose prose-sm md:prose-base max-w-none break-words">
            {message.text.split('\n').map((line, i) => (
              <p key={i} className="mb-3 last:mb-0">
                {line}
              </p>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const LoadingIndicator = () => (
    <div className="flex space-x-2 p-2">
      <div className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce [animation-delay:-0.3s]" />
      <div className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce [animation-delay:-0.15s]" />
      <div className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce" />
    </div>
  );

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">
      <div className="flex-1 overflow-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.map(message => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted p-4 rounded-2xl shadow-sm">
                <LoadingIndicator />
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t p-4 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-3xl mx-auto flex gap-3">
          <Input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !isLoading && handleSend()}
            placeholder="Type your message..."
            className="text-base"
            disabled={isLoading}
          />
          <Button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            size="icon"
          >
            <SendIcon className="h-5 w-5" />
            <span className="sr-only">Send</span>
          </Button>
        </div>
        {error && (
          <p className="mt-3 text-sm text-destructive text-center">{error}</p>
        )}
      </div>
    </div>
  );
};

export default Chat;