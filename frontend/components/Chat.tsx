// src/components/Chat.tsx

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid'; // Import UUID
import { SendIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useTranslation } from 'react-i18next';
import BouncingDots from './BouncingDots';

import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';

// Definicje typów
type Message = {
  id: string; // Zmieniono na string dla UUID
  conversation_id: number;
  text: string;
  sender: 'user' | 'bot';
  created_at: string;
  isNew?: boolean;
  isError?: boolean;
};

interface ChatProps {
  conversationId: number; // usuwamy userId
}

// Definicja interfejsu dla komponentu code
interface CustomCodeProps {
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
}

const Chat: React.FC<ChatProps> = ({ conversationId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';

  // Autoscroll
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Pobieramy wiadomości
  const fetchMessages = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        credentials: 'include', // cookie wędruje w obie strony
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
  }, [API_BASE_URL, conversationId]);

  useEffect(() => {
    if (conversationId) fetchMessages();
  }, [fetchMessages, conversationId]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userInput = input.trim();
    setInput('');

    // Generowanie unikalnego ID dla wiadomości użytkownika
    const userMsgId = uuidv4();

    // Dodajemy wiadomość usera lokalnie
    const userMsg: Message = {
      id: userMsgId,
      conversation_id: conversationId,
      text: userInput,
      sender: 'user',
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      setIsLoading(true);
      setIsTyping(true); // Ustawiamy isTyping na true

      setError('');

      // Zapisujemy wiadomość usera
      const userMessageResponse = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        method: 'POST',
        credentials: 'include', // kluczowe
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: 'user', text: userInput }),
      });

      if (!userMessageResponse.ok) {
        const errData = await userMessageResponse.json();
        throw new Error(errData.detail || 'Error sending user message.');
      }

      // Zapytanie do /query
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

      // Generowanie unikalnego ID dla wiadomości bota
      const botMsgId = uuidv4();

      // Wiadomość bota
      const botMsg: Message = {
        id: botMsgId,
        conversation_id: conversationId,
        text: data.answer,
        sender: 'bot',
        created_at: new Date().toISOString(),
      };

      // Zapisanie wiadomości bota
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

      // Generowanie unikalnego ID dla wiadomości błędu
      const errorMsgId = uuidv4();

      const errorMessage: Message = {
        id: errorMsgId,
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
      setIsTyping(false); // Ustawiamy isTyping na false
    }
  };

  // Definicja komponentów dla ReactMarkdown
  const components: Components = {
    code({ inline, className, children, ...props }: CustomCodeProps) {
      const match = /language-(\w+)/.exec(className || '');
      const { ...rest } = props; // Usunięcie `ref` z props

      return !inline && match ? (
        <SyntaxHighlighter
          {...rest}
          style={oneDark}
          language={match[1]}
          PreTag="div"
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...rest}>
          {children}
        </code>
      );
    },
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      {/* Lista wiadomości */}
      <div className="flex-1 overflow-auto mx-auto p-4 pb-32 w-full">
        {messages.map(msg => {
          const align = msg.sender === 'user' ? 'ml-auto mr-0' : 'mr-auto ml-0';
          const textColor =
            msg.sender === 'user' ? 'text-secondary-foreground' : 'text-foreground';
          return (
            <div key={msg.id} className="flex">
              <div
                className={`inline-block p-3 rounded-lg ${align} max-w-[95%] break-words ${
                  msg.sender === 'user'
                    ? 'bg-secondary'
                    : 'bg-background'
                } ${msg.isError ? 'border border-red-500' : ''} ${textColor}`}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  className="break-words max-w-none text-base sm:text-sm md:text-lg text-secondary-foreground"
                  components={components}
                >
                  {msg.text}
                </ReactMarkdown>
              </div>
            </div>
          );
        })}
        {isLoading && (
          <div className="flex">
            <div className="inline-block p-3 rounded-lg mr-auto max-w-[95%] bg-secondary text-secondary-foreground break-words">
              <BouncingDots />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Pole tekstowe */}
     <div className="border-t p-4">
        <div className="flex justify-center w-full">
          <div className="flex w-[80%]">
            <Input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !isLoading && handleSend()}
              placeholder={t('type_message') || 'Type your message...'}
              className="text-base sm:text-sm md:text-lg text-muted-foreground"
              disabled={isLoading}
            />
            <Button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              variant="default"
              className="ml-2"
            >
              <SendIcon className="h-4 w-4" />
              <span className="sr-only">{t('send')}</span>
            </Button>
          </div>
        </div>
        {error && <p className="mt-2 text-sm sm:text-base text-destructive text-center">{error}</p>}
      </div>
    </div>
  );
};

export default Chat;