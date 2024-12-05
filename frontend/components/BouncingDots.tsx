import React from 'react';

const BouncingDots: React.FC = () => {
  return (
    <div className="flex space-x-1">
      {[1, 2, 3].map((dot) => (
        <div
          key={dot}
          className="w-2 h-2 bg-secondary-foreground rounded-full animate-bounce"
          style={{ animationDelay: `${dot * 0.1}s` }}
        />
      ))}
    </div>
  );
};

export default BouncingDots;

