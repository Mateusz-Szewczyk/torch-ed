// components/TypewriterText.tsx
import React, { useEffect, useState } from 'react';

interface TypewriterTextProps {
  text: string;
  onTypingComplete?: () => void;
}

const TypewriterText: React.FC<TypewriterTextProps> = ({ text, onTypingComplete }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    let currentIndex = 0;
    setDisplayedText(''); // Reset displayed text when text prop changes
    const interval = setInterval(() => {
      setDisplayedText((prev) => prev + text[currentIndex]);
      currentIndex++;
      if (currentIndex === text.length) {
        clearInterval(interval);
        if (onTypingComplete) {
          onTypingComplete();
        }
      }
    }, 5); // Możesz dostosować prędkość tutaj

    return () => clearInterval(interval);
  }, [text, onTypingComplete]);

  return <span>{displayedText}</span>;
};

export default TypewriterText;
