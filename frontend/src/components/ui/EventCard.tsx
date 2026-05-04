import React from 'react';
import { Calendar, Clock, MapPin, Users } from 'lucide-react';
import { StatusBadge, EventStatus } from './StatusBadge';

export interface EventData {
  id: string;
  name: string;
  description: string;
  date: string;
  time: string;
  duration: string;
  capacity: number;
  registered: number;
  status: EventStatus;
  location?: string;
}

interface EventCardProps {
  event: EventData;
  actionButton?: React.ReactNode;
}

export const EventCard = ({ event, actionButton }: EventCardProps) => {
  const isSoldOut = event.registered >= event.capacity;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow flex flex-col h-full">
      <div className="p-5 flex-1">
        <div className="flex justify-between items-start mb-3">
          <StatusBadge status={event.status} />
          <div className="flex items-center text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full">
            <Users className="w-3.5 h-3.5 mr-1" />
            {event.registered}/{event.capacity}
          </div>
        </div>
        
        <h3 className="font-bold text-lg text-brand-900 mb-2 line-clamp-2">{event.name}</h3>
        <p className="text-slate-600 text-sm line-clamp-3 mb-4 flex-1">
          {event.description}
        </p>

        <div className="space-y-2 mt-auto">
          <div className="flex items-center text-sm text-slate-500">
            <Calendar className="w-4 h-4 mr-2 text-brand-500" />
            {event.date}
          </div>
          <div className="flex items-center text-sm text-slate-500">
            <Clock className="w-4 h-4 mr-2 text-brand-500" />
            {event.time} ({event.duration})
          </div>
          {event.location && (
            <div className="flex items-center text-sm text-slate-500">
              <MapPin className="w-4 h-4 mr-2 text-brand-500" />
              {event.location}
            </div>
          )}
        </div>
      </div>
      
      <div className="px-5 py-4 bg-slate-50 border-t border-slate-100">
        {actionButton ? actionButton : (
           <p className="text-sm font-medium text-slate-500 italic">No hay acciones disponibles</p>
        )}
      </div>
    </div>
  );
};
