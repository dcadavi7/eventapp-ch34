import React from 'react';
import { cn } from '@/lib/utils';

export type EventStatus = 'Activo' | 'En curso' | 'Finalizado' | 'Cancelado';

const statusStyles: Record<EventStatus, string> = {
  'Activo': 'bg-green-100 text-green-800 border-green-200',
  'En curso': 'bg-blue-100 text-blue-800 border-blue-200',
  'Finalizado': 'bg-slate-100 text-slate-800 border-slate-200',
  'Cancelado': 'bg-red-100 text-red-800 border-red-200',
};

export const StatusBadge = ({ status, className }: { status: EventStatus, className?: string }) => {
  return (
    <span className={cn("px-2.5 py-0.5 rounded-full text-xs font-semibold border", statusStyles[status], className)}>
      {status}
    </span>
  );
};
