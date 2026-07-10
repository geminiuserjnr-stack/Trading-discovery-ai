import React, { createContext, useContext, useState, useCallback } from 'react';

export type ToastType = 'success' | 'warning' | 'error' | 'info';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  title?: string;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (message: string, type: ToastType, title?: string) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType, title?: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type, title }]);

    // Auto-dismiss after 4 seconds
    setTimeout(() => {
      removeToast(id);
    }, 4000);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast rendering container */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start p-3 rounded border shadow-lg transition-all duration-300 transform translate-y-0 ${
              toast.type === 'success'
                ? 'bg-darkCard border-accentSuccess text-accentSuccess'
                : toast.type === 'warning'
                ? 'bg-darkCard border-accentWarning text-accentWarning'
                : toast.type === 'error'
                ? 'bg-darkCard border-accentDanger text-accentDanger'
                : 'bg-darkCard border-accentPrimary text-accentPrimary'
            }`}
          >
            <div className="flex-1">
              {toast.title && <h4 className="text-sm font-bold uppercase tracking-wider mb-0.5">{toast.title}</h4>}
              <p className="text-xs text-darkText">{toast.message}</p>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-darkMuted hover:text-darkText ml-3 text-sm focus:outline-none"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
