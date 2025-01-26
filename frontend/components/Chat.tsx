// src/components/Chat.tsx

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { SendIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { SyntaxHighlighterProps } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { useTranslation } from 'react-i18next';
import { v4 as uuidv4 } from 'uuid';
import BouncingDots from "@/components/BouncingDots";

// Definicje typów
type Message = {
  id: string;
  conversation_id: number;
  text: string;
  sender: 'user' | 'bot';
  created_at: string;
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
  const { t } = useTranslation();

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';

  // Autoscroll do najnowszej wiadomości
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Fetch wiadomości z API
  const fetchMessages = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        method: 'GET',
      });
      if (res.ok) {
        const data: Message[] = await res.json();
        setMessages(data.map(msg => ({ ...msg, isError: false })));
      } else {
        console.error('Failed to fetch messages:', res.statusText);
      }
    } catch (err) {
      console.error('Error fetching messages:', err);
    }
  }, [API_BASE_URL, conversationId]);

  useEffect(() => {
    if (conversationId) fetchMessages();
  }, [fetchMessages, conversationId]);

  // Funkcja wysyłania wiadomości
  const handleSend = async () => {
    if (!input.trim()) return;
    const userInput = input.trim();
    setInput('');

    const userMsg: Message = {
      id: uuidv4(),
      conversation_id: conversationId,
      text: userInput,
      sender: 'user',
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      setIsLoading(true);
      setError('');

      // Zapisz wiadomość użytkownika
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

      // Endpoint zapytania
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
        id: uuidv4(),
        conversation_id: conversationId,
        text: data.answer,
        sender: 'bot',
        created_at: new Date().toISOString(),
      };

      // Zapisz wiadomość bota
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
        id: uuidv4(),
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

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      {/* Lista wiadomości */}
      <div className="flex-1 overflow-auto mx-auto p-4 pb-32 w-full md:w-4/5">
        {messages.map((message) => {
          const alignmentClass =
            message.sender === 'user'
              ? 'ml-auto mr-0'
              : 'mr-auto ml-0';
          return (
            <div key={message.id} className="flex">
              <div
                className={`inline-block p-3 rounded-lg ${alignmentClass} max-w-full sm:max-w-4/5 break-words ${
                  message.sender === 'user'
                    ? 'bg-secondary text-secondary-foreground'
                    : 'bg-background text-foreground'
                }`}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  className="prose dark:prose-invert break-words max-w-none"
                  components={{
                    code({ className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      const language = match ? match[1] : '';
                      const isInline = !match;

                      return isInline ? (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      ) : (
                        <SyntaxHighlighter
                          style={oneDark}
                          language={language}
                          PreTag="div"
                          {...(props as SyntaxHighlighterProps)}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
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
        {isLoading && (
          <div className="flex">
            <div className="inline-block p-3 rounded-lg mr-auto max-w-full sm:max-w-4/5 bg-secondary text-secondary-foreground break-words">
              <BouncingDots />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      {/* Pole tekstowe */}
      <div className="border-t border-border p-4 w-full bg-background">
        <div className="flex justify-center mx-auto w-full md:w-4/5">
          <div className="flex gap-2 w-full">
            <div className="flex-grow">
              <Input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleSend()}
                placeholder={t('type_message') || 'Type your message...'}
                className="flex-1 text-base sm:text-sm md:text-sm text-muted-foreground"
                disabled={isLoading}
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              variant="default"
              className="shrink-0"
            >
              <SendIcon className="h-4 w-4" />
              <span className="sr-only">{t('send')}</span>
            </Button>
          </div>
        </div>
        {error && (
          <p className="mt-2 text-sm sm:text-base text-destructive text-center">
            {error}
          </p>
        )}
      </div>
    </div>
  );
};

export default Chat;
