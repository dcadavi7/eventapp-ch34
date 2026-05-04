"use client";

import React, { useState, useEffect } from 'react';
import { EventCard, EventData } from '@/components/ui/EventCard';
import { useAuth } from '@/providers/AuthProvider';
import { eventService } from '@/services/eventService';

export default function ProfilePage() {
  const { user } = useAuth();
  const [myEvents, setMyEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMisEventos = async () => {
      const data = await eventService.getMisEventosRegistrados();
      setMyEvents(data);
      setLoading(false);
    };
    fetchMisEventos();
  }, []);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 mb-8 flex items-center gap-6">
        <div className="w-20 h-20 bg-brand-100 text-brand-700 rounded-full flex items-center justify-center text-2xl font-bold">
          {user?.name?.charAt(0) || 'U'}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-brand-900">{user?.name}</h1>
          <p className="text-slate-500 mt-1">{user?.email} • Rol: {user?.role}</p>
        </div>
      </div>

      <div className="mb-6">
        <h2 className="text-xl font-bold text-brand-900">Mis Eventos Registrados</h2>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-64 bg-slate-100 rounded-xl animate-pulse"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {myEvents.map((evt) => (
            <EventCard 
              key={evt.id} 
              event={evt} 
              actionButton={
                <button 
                  disabled
                  className="w-full py-2.5 px-4 rounded-md text-sm font-medium bg-slate-100 text-slate-500 cursor-default"
                >
                  Registro Confirmado
                </button>
              }
            />
          ))}
          {myEvents.length === 0 && (
             <div className="col-span-full py-12 text-center text-slate-500 bg-white rounded-xl border border-dashed border-slate-300">
               Aún no te has registrado a ningún evento.
             </div>
          )}
        </div>
      )}
    </div>
  );
}
