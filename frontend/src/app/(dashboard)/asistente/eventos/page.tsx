"use client";

import React, { useState, useEffect } from 'react';
import { EventCard, EventData } from '@/components/ui/EventCard';
import { Toast, ToastType } from '@/components/ui/Toast';
import { eventService } from '@/services/eventService';
import { useAuth } from '@/providers/AuthProvider';

export default function CatalogPage() {
  const { user } = useAuth();
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Toast State
  const [toast, setToast] = useState<{message: string, type: ToastType, visible: boolean}>({
    message: '', type: 'info', visible: false
  });

  const showToast = (message: string, type: ToastType) => {
    setToast({ message, type, visible: true });
  };

  useEffect(() => {
    // Simulando llamada a API Gateway Endpoint GET /eventos/activos
    const fetchEventos = async () => {
      try {
        setLoading(true);
        const data = await eventService.getEventosActivos();
        setEvents(data);
        setLoading(false);
      } catch (error) {
        showToast("Error conectando con API Gateway.", "error");
        setLoading(false);
      }
    };
    fetchEventos();
  }, []);

  const handleRegister = async (event: EventData) => {
    if (!user) {
      showToast("Debes iniciar sesión para registrarte en eventos.", "error");
      return;
    }

    try {
      setLoading(true);
      await eventService.registerToEvent({
        eventId: event.id,
        userId: user.email, // Usamos el email como ID por ahora si no hay uno específico
        name: user.name,
        email: user.email
      });
      
      showToast(`Te has registrado a "${event.name}" exitosamente.`, "success");
      
      // Actualizar la lista localmente (opcional, mejor re-fetch)
      const updatedEvents = await eventService.getEventosActivos();
      setEvents(updatedEvents);
      
      setLoading(false);
    } catch (error: any) {
      setLoading(false);
      const message = error.response?.data?.message || error.message;
      
      if (message.includes("cupos") || message.includes("disponible") || message.includes("agotado")) {
        showToast("No se pudo completar el registro: el evento no está disponible o no hay cupos.", "error");
      } else if (message.includes("ya se encuentra registrado")) {
        showToast("Ya estás registrado en este evento.", "info");
      } else {
        showToast(`Error al registrarse: ${message}`, "error");
      }
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-brand-900">Lista de eventos</h1>
        <p className="text-slate-600 mt-1">Explora los eventos activos y reserva tu cupo.</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {[1,2,3].map(i => (
            <div key={i} className="h-64 bg-slate-100 rounded-xl animate-pulse"></div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {events.map((evt) => {
             const isSoldOut = evt.registered >= evt.capacity;
             return (
              <EventCard 
                key={evt.id} 
                event={evt} 
                actionButton={
                  <button 
                    onClick={() => handleRegister(evt)}
                    disabled={isSoldOut}
                    className={`w-full py-2.5 px-4 rounded-md text-sm font-medium transition-colors ${
                      isSoldOut 
                        ? 'bg-slate-200 text-slate-500 cursor-not-allowed' 
                        : 'bg-brand-600 text-white hover:bg-brand-700'
                    }`}
                  >
                    {isSoldOut ? 'Cupo Agotado' : 'Registrarme al Evento'}
                  </button>
                }
              />
            )
          })}
        </div>
      )}

      <Toast 
        isVisible={toast.visible} 
        message={toast.message} 
        type={toast.type} 
        onClose={() => setToast({...toast, visible: false})} 
      />
    </div>
  );
}
