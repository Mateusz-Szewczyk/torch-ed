'use client';

import { useState } from 'react';
import { SendIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';

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

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const createFormData = (data: { user_id: string; query: string }): FormData => {
    const formData = new FormData();
    formData.append('user_id', data.user_id);
    formData.append('query', data.query);
    return formData;
  };

  const handleSend = async () => {
    if (input.trim()) {
      const currentInput = input; // Zapisz aktualną wartość input
      const userMessage: Message = {
        id: Date.now(),
        text: currentInput,
        sender: 'user',
      };
      setMessages((prevMessages) => [...prevMessages, userMessage]);
      setInput('');

      try {
        setIsLoading(true);
        const response = await fetch('http://localhost:8042/query/', {
          method: 'POST',
          body: createFormData({
            user_id: 'user123',
            query: currentInput, // Użyj zapisanej wartości input
          }),
        });

        if (!response.ok) {
          throw new Error(`Błąd sieciowy: ${response.statusText}`);
        }

        const data: QueryResponse = await response.json();
        console.log('API Response:', data); // Opcjonalne logowanie odpowiedzi API

        const botMessage: Message = {
          id: Date.now(),
          text: data.answer,
          sender: 'bot',
        };

        setMessages((prevMessages) => [...prevMessages, botMessage]);
      } catch (error: unknown) {
        console.error('Błąd podczas komunikacji z API:', error);

        let errorMessageText = 'Przepraszamy, wystąpił błąd. Spróbuj ponownie później.';

        if (error instanceof Error) {
          errorMessageText = `Przepraszamy, wystąpił błąd: ${error.message}. Spróbuj ponownie później.`;
        }

        const errorMessage: Message = {
          id: Date.now(),
          text: errorMessageText,
          sender: 'bot',
        };
        setMessages((prevMessages) => [...prevMessages, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="flex flex-col h-full bg-background text-foreground">
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.sender === 'user' ? 'justify-end' : 'justify-start'
              }`}
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
                Piszę odpowiedź...
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
            placeholder="Wpisz wiadomość..."
            className="flex-1"
            disabled={isLoading}
          />
          <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
            <SendIcon className="h-4 w-4" />
            <span className="sr-only">Wyślij</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
