// components/Chat.tsx
'use client';

import React, { useState, useEffect, useRef } from 'react';
import { SendIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useTranslation } from 'react-i18next';
import BouncingDots from './BouncingDots';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';

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
  userId: string;
  conversationId: number;
}

const Chat: React.FC<ChatProps> = ({ userId, conversationId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api';

  // Automatyczne przewijanie do dołu przy dodaniu wiadomości
  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  // Pobieranie wiadomości
  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`);
        if (response.ok) {
          const data: Message[] = await response.json();
          const loadedMessages = data.map((msg) => ({
            ...msg,
            isNew: false,
            isError: false,
          }));
          setMessages(loadedMessages);
        } else {
          console.error('Failed to fetch messages:', response.statusText);
        }
      } catch (err) {
        console.error('Error fetching messages:', err);
      }
    };

    if (conversationId) {
      fetchMessages();
    }
  }, [conversationId, API_BASE_URL]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const currentInput = input.trim();
    setInput('');

    const userMessage: Message = {
      id: Date.now(),
      conversation_id: conversationId,
      text: currentInput,
      sender: 'user',
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);

    try {
      setIsLoading(true);
      setError('');

      await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: 'user', text: currentInput }),
      });

      const response = await fetch(`${API_BASE_URL}/query/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          conversation_id: conversationId,
          query: currentInput,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const errorDetail = errorData.detail;
        if (Array.isArray(errorDetail)) {
          const msgs = errorDetail.map((err: any) => `${err.loc.join('.')}: ${err.msg}`).join('; ');
          throw new Error(msgs);
        } else {
          throw new Error(
            errorDetail || t('error_network', { statusText: response.statusText })
          );
        }
      }

      const data = await response.json();

      const botMessage: Message = {
        id: Date.now() + 1,
        conversation_id: conversationId,
        text: data.answer,
        sender: 'bot',
        created_at: new Date().toISOString(),
        isNew: false,
      };

      await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: 'bot', text: data.answer }),
      });

      setMessages((prev) => [...prev, botMessage]);
      setIsTyping(false);
    } catch (err: unknown) {
      console.error(t('error_api'), err);

      let errorMessageText = t('error_generic');
      if (err instanceof Error) {
        errorMessageText = err.message;
      } else if (typeof err === 'object' && err !== null) {
        errorMessageText = JSON.stringify(err);
      } else if (typeof err === 'string') {
        errorMessageText = err;
      }

      const errorMessage: Message = {
        id: Date.now() + 2,
        conversation_id: conversationId,
        text: errorMessageText,
        sender: 'bot',
        created_at: new Date().toISOString(),
        isNew: false,
        isError: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
      setError(errorMessageText);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center">
      {/* Kontener wiadomości */}
      <div className="w-3/5 pt-4 pb-32 space-y-4">
        {messages.map((message) => {
          const alignmentClass =
            message.sender === 'user'
              ? 'ml-auto mr-0'
              : 'mr-auto ml-0';

          return (
            <div key={message.id} className="flex">
              <div
                className={`inline-block p-3 rounded-lg ${alignmentClass} max-w-[80%] break-words ${
                  message.sender === 'user'
                    ? 'bg-secondary text-secondary-foreground'
                    : 'bg-background text-foreground'
                }`}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  className="prose dark:prose-invert break-words max-w-none"
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
                        <SyntaxHighlighter
                          {...props}
                          style={oneDark}
                          language={match[1]}
                          PreTag="div"
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {message.text}
                </ReactMarkdown>
              </div>
            </div>
          );
        })}
        {(isLoading || isTyping) && (
          <div className="flex">
            <div className="inline-block p-3 rounded-lg mr-auto max-w-[80%] bg-secondary text-secondary-foreground break-words">
              <BouncingDots />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Pasek wpisywania wiadomości – wyśrodkowany i dopasowany */}
      <div className="fixed bottom-0 w-full bg-background border-t border-border p-4">
        <div className="max-w-3xl mx-auto flex space-x-2">
          <Input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isTyping && handleSend()}
            placeholder={t('type_message')}
            className="flex-1"
            disabled={isLoading || isTyping}
          />
          <Button
            onClick={handleSend}
            disabled={isLoading || !input.trim() || isTyping}
            variant="primary"
          >
            <SendIcon className="h-4 w-4" />
            <span className="sr-only">{t('send')}</span>
          </Button>
        </div>
        {error && <p className="mt-2 text-sm text-destructive text-center">{error}</p>}
      </div>
    </div>
  );
};

export default Chat;
