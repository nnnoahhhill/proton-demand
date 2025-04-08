"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Spinner } from '@/components/ui/spinner';

interface LoadingContextType {
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  showLoadingOverlay: () => void;
  hideLoadingOverlay: () => void;
}

const LoadingContext = createContext<LoadingContextType>({
  isLoading: false,
  setLoading: () => {},
  showLoadingOverlay: () => {},
  hideLoadingOverlay: () => {},
});

export const useLoading = () => useContext(LoadingContext);

export function LoadingProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(false);

  const setLoading = (loading: boolean) => {
    setIsLoading(loading);
  };

  const showLoadingOverlay = () => {
    setIsLoading(true);
  };

  const hideLoadingOverlay = () => {
    setIsLoading(false);
  };

  return (
    <LoadingContext.Provider
      value={{
        isLoading,
        setLoading,
        showLoadingOverlay,
        hideLoadingOverlay,
      }}
    >
      {children}
      {isLoading && (
        <div className="fixed inset-0 bg-[#0A1525]/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="flex flex-col items-center justify-center p-8 rounded-lg">
            <Spinner size={120} />
            <p className="mt-6 text-xl text-white font-andale">Processing...</p>
            <p className="mt-2 text-white/70 font-avenir">Please wait</p>
          </div>
        </div>
      )}
    </LoadingContext.Provider>
  );
}
