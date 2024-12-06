// components/Blob.tsx
import React from 'react';

interface BlobProps {
  size: number; // Rozmiar bloba w pikselach
  top: string; // Pozycja od góry (np. '10%', '50px')
  left: string; // Pozycja od lewej (np. '20%', '100px')
  color: string; // Kolor w formacie HSL (bez 'hsl()', np. '45 20% 94%')
  animationDuration: number; // Czas trwania animacji w sekundach
  animationDelay: number; // Opóźnienie animacji w sekundach
}

const Blob: React.FC<BlobProps> = ({
  size,
  top,
  left,
  color,
  animationDuration,
  animationDelay,
}) => {
  return (
    <div
      className="absolute rounded-full opacity-50 filter blur-3xl animate-blob"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        top: top,
        left: left,
        background: `radial-gradient(circle at center, hsl(${color}), hsl(var(--popover)), hsl(var(--accent)))`,
        animationDuration: `${animationDuration}s`,
        animationDelay: `${animationDelay}s`,
      }}
    ></div>
  );
};

export default Blob;
