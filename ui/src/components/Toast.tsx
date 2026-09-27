import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

type Variant = "success" | "danger";

interface ToastItem {
  id: number;
  message: string;
  variant: Variant;
}

interface ToastContextValue {
  notify: (message: string, variant?: Variant) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);
const DISMISS_AFTER_MS = 5000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const notify = useCallback((message: string, variant: Variant = "success") => {
    const id = nextId.current++;
    setToasts((prev) => [...prev, { id, message, variant }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, DISMISS_AFTER_MS);
  }, []);

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.variant}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
