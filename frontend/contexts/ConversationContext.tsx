// contexts/ConversationContext.tsx

import React, { createContext, useState } from 'react';

interface ConversationContextProps {
  currentConversationId: number | null;
  setCurrentConversationId: (id: number | null) => void;
}

export const ConversationContext = createContext<ConversationContextProps>({
  currentConversationId: null,
  setCurrentConversationId: () => {},
});

export const ConversationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);

  return (
    <ConversationContext.Provider value={{ currentConversationId, setCurrentConversationId }}>
      {children}
    </ConversationContext.Provider>
  );
};
