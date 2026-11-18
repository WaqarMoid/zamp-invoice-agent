import React, { createContext, useContext, useState, useCallback } from "react";

interface ToastContextType {
  showToast: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toast, setToast] = useState<{ id: number; message: string } | null>(null);

  const showToast = useCallback((message: string) => {
    const id = Date.now();
    setToast({ id, message });
    setTimeout(() => {
      setToast((current) => (current?.id === id ? null : current));
    }, 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-6 right-6 z-50 bg-[var(--ink)] text-white px-4 py-3 rounded-[8px] shadow-[var(--shadow-2)] font-sans text-[14px] leading-[20px] animate-in fade-in slide-in-from-bottom-2 duration-150 select-none max-w-sm"
        >
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  );
};

export function useToast(): ToastContextType {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    return { showToast: (msg: string) => console.log("Toast:", msg) };
  }
  return ctx;
}
