// components/CustomTooltip.tsx

'use client';

import React, { useState, useRef, useEffect} from 'react';
import ReactDOM from 'react-dom';

interface CustomTooltipProps {
  content: string;
  children: React.ReactElement;
}

export const CustomTooltip: React.FC<CustomTooltipProps> = ({ content, children }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [tooltipStyle, setTooltipStyle] = useState<React.CSSProperties>({});
  const tooltipRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        tooltipRef.current &&
        !tooltipRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setIsVisible(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    if (isVisible && triggerRef.current && tooltipRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();

      // Oblicz pozycję tooltipu
      const top = triggerRect.top - tooltipRect.height - 8; // 8px odstęp
      const left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;

      setTooltipStyle({
        top: top < 0 ? triggerRect.bottom + 8 : top, // Jeśli za wysoko, pokaż poniżej
        left: Math.max(8, Math.min(left, window.innerWidth - tooltipRect.width - 8)), // Zapobiega wyjściu poza ekran
      });
    }
  }, [isVisible]);

  const handleMouseEnter = () => {
    setIsVisible(true);
  };

  const handleMouseLeave = () => {
    setIsVisible(false);
  };

  // Tworzymy portal, jeśli DOM jest dostępny
  const tooltip = isVisible ? (
    ReactDOM.createPortal(
      <div
        ref={tooltipRef}
        className="absolute z-50 px-3 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg shadow-sm dark:bg-gray-700 transition-opacity duration-300"
        style={{
          position: 'fixed',
          maxWidth: '300px',
          ...tooltipStyle,
        }}
      >
        {content}
      </div>,
      document.body
    )
  ) : null;

  return (
    <>
      <div
        className="relative inline-block"
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {children}
      </div>
      {tooltip}
    </>
  );
};
