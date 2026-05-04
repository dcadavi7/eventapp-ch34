import React, { useEffect } from 'react';
import { CheckCircle, Info, XCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
  message: string;
  type?: ToastType;
  isVisible: boolean;
  onClose: () => void;
}

export const Toast = ({ message, type = 'info', isVisible, onClose }: ToastProps) => {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  if (!isVisible) return null;

  const typeConfig = {
    success: { icon: CheckCircle, className: 'bg-green-50 text-green-800 border-green-200' },
    error: { icon: XCircle, className: 'bg-red-50 text-red-800 border-red-200' },
    info: { icon: Info, className: 'bg-blue-50 text-blue-800 border-blue-200' }
  };

  const Icon = typeConfig[type].icon;

  return (
    <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-5 fade-in duration-300">
      <div className={cn("flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg max-w-sm", typeConfig[type].className)}>
        <Icon className="w-5 h-5 flex-shrink-0" />
        <p className="text-sm font-medium mr-2">{message}</p>
        <button onClick={onClose} className="p-1 hover:bg-black/5 rounded-full transition-colors ml-auto">
          <X className="w-4 h-4 opacity-70" />
        </button>
      </div>
    </div>
  );
};
