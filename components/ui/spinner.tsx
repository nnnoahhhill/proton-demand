"use client";

import { useEffect, useState } from 'react';
import Image from 'next/image';

interface SpinnerProps {
  size?: number;
}

export function Spinner({ size = 100 }: SpinnerProps) {
  const [isBlueActive, setIsBlueActive] = useState(true);

  useEffect(() => {
    const intervalId = setInterval(() => {
      setIsBlueActive(prev => !prev);
    }, 3000); // Switch colors every 3 seconds

    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="relative" style={{ width: `${size}px`, height: `${size}px` }}>
      {/* Blue spinner */}
      <div
        className={`absolute inset-0 transition-opacity duration-800 ${isBlueActive ? 'opacity-100' : 'opacity-0'}`}
        style={{ animationPlayState: isBlueActive ? 'running' : 'paused' }}
      >
        <div className="w-full h-full animate-[spin-slow_2.5s_cubic-bezier(0.25,0.1,0.25,1)_infinite]">
          <Image
            src="/blue.png"
            alt="Loading"
            width={size}
            height={size}
            priority
            className="animate-[pulse-subtle_1s_cubic-bezier(0.4,0,0.2,1)_infinite]"
          />
        </div>
      </div>

      {/* Green spinner */}
      <div
        className={`absolute inset-0 transition-opacity duration-800 ${!isBlueActive ? 'opacity-100' : 'opacity-0'}`}
        style={{ animationPlayState: !isBlueActive ? 'running' : 'paused' }}
      >
        <div className="w-full h-full animate-[spin-slow_2.5s_cubic-bezier(0.25,0.1,0.25,1)_infinite]">
          <Image
            src="/green.png"
            alt="Loading"
            width={size}
            height={size}
            priority
            className="animate-[pulse-subtle_1s_cubic-bezier(0.4,0,0.2,1)_infinite]"
          />
        </div>
      </div>
    </div>
  );
}
