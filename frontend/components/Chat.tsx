// components/Chat.tsx
'use client';

import React, { useState, useEffect, useRef } from 'react';
import { SendIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTranslation } from 'react-i18next';
import BouncingDots from './BouncingDots';
import TypewriterText from './TypewriterText';

type Message = {
  id: number;
  conversation_id: number;
  text: string;
  sender: 'user' | 'bot';
  created_at: string;
  isNew?: boolean; // Oznacza, czy wiadomość jest nowa (od bota)
  isError?: boolean; // Oznacza, czy wiadomość jest błędem
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
  const scrollRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null); // Nowa referencja
  const { t } = useTranslation();
  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api';

  // Automatyczne przewijanie na dół
  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  // Fetch messages for the conversation
  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/chats/${conversationId}/messages/`
        );
        if (response.ok) {
          const data: Message[] = await response.json();
          // Oznacz wszystkie załadowane wiadomości jako nie-nowe i nie-błędy
          const loadedMessages = data.map(msg => ({
            ...msg,
            isNew: false,
            isError: false,
          }));
          setMessages(loadedMessages);
        } else {
          console.error('Failed to fetch messages:', response.statusText);
        }
      } catch (error) {
        console.error('Error fetching messages:', error);
      }
    };

    if (conversationId) {
      fetchMessages();
    }
  }, [conversationId, API_BASE_URL]);

  const handleSend = async () => {
    if (input.trim()) {
      const currentInput = input.trim();
      setInput('');

      const userMessage: Message = {
        id: Date.now(),
        conversation_id: conversationId,
        text: currentInput,
        sender: 'user',
        created_at: new Date().toISOString(),
      };

      setMessages((prevMessages) => [...prevMessages, userMessage]);

      try {
        setIsLoading(true);
        setError('');

        // Save user's message to the database
        await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sender: 'user',
            text: currentInput,
          }),
        });

        // Send query to the bot with added conversation_id
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
            const messages = errorDetail
              .map((err: any) => `${err.loc.join('.')}: ${err.msg}`)
              .join('; ');
            throw new Error(messages);
          } else {
            throw new Error(
              errorDetail ||
                t('error_network', { statusText: response.statusText })
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
          isNew: true, // Oznacz jako nową wiadomość
        };

        // Save bot's response to the database
        await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sender: 'bot',
            text: data.answer,
          }),
        });

        // Add bot's message and set isTyping to true
        setMessages((prevMessages) => [...prevMessages, botMessage]);
        setIsLoading(false);
        setIsTyping(true); // Set isTyping to true when bot starts typing
      } catch (error: unknown) {
        console.error(t('error_api'), error);

        let errorMessageText = t('error_generic');

        if (error instanceof Error) {
          errorMessageText = error.message;
        } else if (typeof error === 'object' && error !== null) {
          errorMessageText = JSON.stringify(error);
        } else if (typeof error === 'string') {
          errorMessageText = error;
        }

        const errorMessage: Message = {
          id: Date.now() + 2,
          conversation_id: conversationId,
          text: errorMessageText,
          sender: 'bot',
          created_at: new Date().toISOString(),
          isNew: true, // Oznacz jako nową wiadomość
          isError: true, // Oznacz jako wiadomość o błędzie
        };

        setMessages((prevMessages) => [...prevMessages, errorMessage]);
        setError(errorMessageText);
      } finally {
        setIsLoading(false); // Move this after setting isTyping
      }
    }
  };

  return (
    <div className="flex flex-col h-full bg-background text-foreground">
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message, index) => {
            const isLastMessage = index === messages.length - 1;
            return (
              <div
                key={message.id}
                className={`flex ${
                  message.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`inline-block w-auto max-w-[75%] p-3 rounded-lg ${
                    message.sender === 'user'
                      ? 'bg-secondary text-secondary-foreground'
                      : 'bg-background text-foreground'
                  }`}
                >
                  {message.sender === 'bot' && message.isNew && !message.isError ? (
                    <TypewriterText
                      text={message.text}
                      onTypingComplete={
                        isLastMessage && isTyping
                          ? () => setIsTyping(false)
                          : undefined
                      }
                    />
                  ) : (
                    message.text
                  )}
                </div>
              </div>
            );
          })}
          {(isLoading || isTyping) && (
            <div className="flex justify-start">
              <div className="inline-block w-auto max-w-[75%] p-3 rounded-lg bg-secondary text-secondary-foreground">
                <BouncingDots />
              </div>
            </div>
          )}
          <div ref={endRef} /> {/* Dummy div for scrollIntoView */}
        </div>
      </ScrollArea>
      <div className="border-t border-border p-4">
        <div className="flex space-x-2">
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
        {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      </div>
    </div>
  );
};

export default Chat;
