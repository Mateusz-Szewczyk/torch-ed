'use client';

import React, { useState, useEffect, useRef } from 'react';
import { SendIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTranslation } from 'react-i18next';

type Message = {
  id: number;
  text: string;
  sender: 'user' | 'bot';
};

interface QueryResponse {
  user_id: string;
  query: string;
  answer: string;
}

interface ChatProps {
  userId: string;
}

const Chat: React.FC<ChatProps> = ({ userId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { t } = useTranslation();
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api';

  const createFormData = (data: { user_id: string; query: string }): FormData => {
    const formData = new FormData();
    formData.append('user_id', data.user_id);
    formData.append('query', data.query);
    return formData;
  };

  const handleSend = async () => {
    if (input.trim()) {
      const currentInput = input.trim();
      const userMessage: Message = {
        id: Date.now(),
        text: currentInput,
        sender: 'user',
      };
      setMessages((prevMessages) => [...prevMessages, userMessage]);
      setInput('');

      try {
        setIsLoading(true);
        setError(null);
        setSuccessMessage(null);

        const response = await fetch(`${API_BASE_URL}/query/`, {
          method: 'POST',
          body: createFormData({
            user_id: userId,
            query: currentInput,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || t('error_network', { statusText: response.statusText }));
        }

        const data: QueryResponse = await response.json();

        const botMessage: Message = {
          id: Date.now(),
          text: data.answer,
          sender: 'bot',
        };

        setMessages((prevMessages) => [...prevMessages, botMessage]);
        setSuccessMessage(t('response_received'));
      } catch (error: unknown) {
        console.error(t('error_api'), error);

        const errorMessageText =
          error instanceof Error
            ? t('error_generic_with_message', { message: error.message })
            : t('error_generic');

        const errorMessage: Message = {
          id: Date.now(),
          text: errorMessageText,
          sender: 'bot',
        };

        setMessages((prevMessages) => [...prevMessages, errorMessage]);
        setError(errorMessageText);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full bg-background text-foreground">
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`inline-block w-auto max-w-[75%] p-3 rounded-lg ${
                  message.sender === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground'
                }`}
              >
                {message.text}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="inline-block w-auto max-w-[75%] p-3 rounded-lg bg-secondary text-secondary-foreground">
                {t('writing_response')}
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
      <div className="border-t border-border p-4">
        <div className="flex space-x-2">
          <Input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder={t('type_message')}
            className="flex-1"
            disabled={isLoading}
          />
          <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
            <SendIcon className="h-4 w-4" />
            <span className="sr-only">{t('send')}</span>
          </Button>
        </div>
        {successMessage && <p className="mt-2 text-sm text-green-600">{successMessage}</p>}
        {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      </div>
    </div>
  );
};

export default Chat;
