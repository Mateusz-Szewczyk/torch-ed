import React, { useState, useEffect, useRef } from 'react';
import { SendIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import ReactMarkdown from 'react-markdown';

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
      <div className="flex">
        <div
          className={`inline-block p-3 rounded-lg ${
            isUser ? 'ml-auto mr-0' : 'mr-auto ml-0'
          } max-w-[95%] break-words ${
            isUser ? 'bg-secondary' : 'bg-background'
          } ${message.isError ? 'border border-red-500' : ''} ${
            isUser ? 'text-secondary-foreground' : 'text-foreground'
          }`}
        >
          <div className="break-words max-w-none text-base sm:text-sm md:text-lg">
            <ReactMarkdown>{message.text}</ReactMarkdown>
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
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      <div className="flex-1 overflow-auto mx-auto p-4 pb-32 w-[85%]">
        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="flex">
            <div className="inline-block p-3 rounded-lg mr-auto max-w-[95%] bg-secondary text-secondary-foreground break-words">
              <LoadingIndicator />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="border-t p-4">
        <div className="flex justify-center max-w-5xl mx-auto">
          <div className="flex gap-2 w-[80%]">
            <div className="flex-grow">
              <Input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !isLoading && handleSend()}
                placeholder="Type your message..."
                className="text-base sm:text-sm md:text-lg text-muted-foreground"
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
              <span className="sr-only">Send</span>
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