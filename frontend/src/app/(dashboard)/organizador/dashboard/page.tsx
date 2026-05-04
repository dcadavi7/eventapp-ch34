"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { PlusCircle, FileText, Settings, XCircle, CheckCircle2, Trash2, BellRing, Send, X } from 'lucide-react';
import { EventCard, EventData } from '@/components/ui/EventCard';
import { Toast, ToastType } from '@/components/ui/Toast';
import { eventService } from '@/services/eventService';
import { useAuth } from '@/providers/AuthProvider';

export default function OrganizadorDashboard() {
  const { user } = useAuth();
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{message: string, type: ToastType, visible: boolean}>({
    message: '', type: 'info', visible: false
  });
  const [activeNotif, setActiveNotif] = useState<string | null>(null);
  const [notifSubject, setNotifSubject] = useState('');
  const [notifMessage, setNotifMessage] = useState('');
  const [sendingNotif, setSendingNotif] = useState(false);

  const showToast = (message: string, type: ToastType) => {
    setToast({ message, type, visible: true });
  };

  useEffect(() => {
    const fetchAll = async () => {
      const data = await eventService.getAllEventos();
      setEvents(data);
      setLoading(false);
    };
    fetchAll();
  }, []);

  const handleEstado = async (id: string, newStatus: string) => {
    try {
      const apiStatus = newStatus === 'Activo' ? 'PROGRAMADO' :
                        newStatus === 'En curso' ? 'EN_CURSO' :
                        newStatus === 'Finalizado' ? 'FINALIZADO' :
                        newStatus === 'Cancelado' ? 'CANCELADO' : newStatus;

      await eventService.updateEvent(id, { status: apiStatus });
      setEvents(events.map((ev: EventData) => ev.id === id ? { ...ev, status: newStatus as any } : ev));
      showToast(`El evento ha cambiado a estado: ${newStatus}`, "success");
    } catch (error) {
      console.error("Error updating status", error);
      showToast("Error al actualizar el estado del evento", "error");
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("¿Estás seguro de que deseas eliminar este evento? Esta acción no se puede deshacer.")) {
      return;
    }
    try {
      await eventService.deleteEvent(id);
      setEvents(events.filter((ev: EventData) => ev.id !== id));
      showToast("Evento eliminado correctamente", "success");
    } catch (error) {
      console.error("Error deleting event", error);
      showToast("Ocurrió un error al intentar eliminar el evento", "error");
    }
  };

  const solicitarReporte = async (eventId: string) => {
    if (!user?.email) {
      showToast("No se pudo determinar tu correo para enviar el reporte.", "error");
      return;
    }
    try {
      await eventService.requestReport(eventId, user.email);
      showToast("Reporte solicitado. Lo recibirás en tu correo en breve.", "success");
    } catch (error) {
      showToast("Error al solicitar el reporte.", "error");
    }
  };

  const handleOpenNotif = (eventId: string) => {
    setActiveNotif(eventId);
    setNotifSubject('');
    setNotifMessage('');
  };

  const handleSendNotif = async (eventId: string) => {
    if (!notifSubject.trim() || !notifMessage.trim()) {
      showToast("El asunto y el mensaje son obligatorios.", "error");
      return;
    }
    try {
      setSendingNotif(true);
      await eventService.sendNotification(eventId, notifSubject.trim(), notifMessage.trim());
      showToast("Notificación encolada. Los asistentes recibirán el correo en breve.", "success");
      setActiveNotif(null);
    } catch (error) {
      showToast("Error al enviar la notificación masiva.", "error");
    } finally {
      setSendingNotif(false);
    }
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-brand-900">Panel de Organización</h1>
          <p className="text-slate-600 mt-1">Gestiona eventos e interactúa con el ciclo de vida.</p>
        </div>
        <Link 
          href="/organizador/eventos/crear" 
          className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2.5 rounded-md font-medium hover:bg-brand-700 transition"
        >
          <PlusCircle className="w-5 h-5" />
          Crear Evento
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="h-64 bg-slate-100 rounded-xl animate-pulse"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {events.map((evt) => (
            <div key={evt.id} className="flex flex-col gap-2">
              <EventCard
                event={evt}
                actionButton={
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => solicitarReporte(evt.id)}
                      className="flex justify-center items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition"
                    >
                      <FileText className="w-3.5 h-3.5" /> Reporte
                    </button>
                    <Link
                      href={`/organizador/eventos/crear?edit=${evt.id}`}
                      className="flex justify-center items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition"
                    >
                      <Settings className="w-3.5 h-3.5" /> Editar
                    </Link>
                    <button
                      onClick={() => handleDelete(evt.id)}
                      className="flex justify-center items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold bg-white border border-red-200 text-red-600 hover:bg-red-50 transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Eliminar
                    </button>
                    <button
                      onClick={() => activeNotif === evt.id ? setActiveNotif(null) : handleOpenNotif(evt.id)}
                      className="flex justify-center items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 transition"
                    >
                      <BellRing className="w-3.5 h-3.5" /> Notificar
                    </button>
                    {evt.status === 'Activo' && (
                      <>
                        <button
                          onClick={() => handleEstado(evt.id, 'Cancelado')}
                          className="flex justify-center items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold bg-red-50 border border-red-200 text-red-700 hover:bg-red-100 transition"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Cancelar
                        </button>
                        <button
                          onClick={() => handleEstado(evt.id, 'En curso')}
                          className="flex justify-center items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 transition"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Iniciar
                        </button>
                      </>
                    )}
                    {evt.status === 'En curso' && (
                      <button
                        onClick={() => handleEstado(evt.id, 'Finalizado')}
                        className="col-span-2 flex justify-center items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold bg-slate-800 border border-slate-700 text-white hover:bg-slate-900 transition"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Marcar como Finalizado
                      </button>
                    )}
                  </div>
                }
              />
              {activeNotif === evt.id && (
                <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 flex flex-col gap-3">
                  <div className="flex justify-between items-center">
                    <p className="text-sm font-semibold text-indigo-800">Notificar a todos los asistentes</p>
                    <button onClick={() => setActiveNotif(null)} className="text-indigo-400 hover:text-indigo-600">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <input
                    type="text"
                    placeholder="Asunto del correo"
                    value={notifSubject}
                    onChange={e => setNotifSubject(e.target.value)}
                    className="w-full rounded-md border border-indigo-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                  <textarea
                    placeholder="Cuerpo del mensaje..."
                    value={notifMessage}
                    onChange={e => setNotifMessage(e.target.value)}
                    rows={3}
                    className="w-full rounded-md border border-indigo-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
                  />
                  <button
                    onClick={() => handleSendNotif(evt.id)}
                    disabled={sendingNotif}
                    className="flex justify-center items-center gap-2 py-2 px-4 rounded-md text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition"
                  >
                    <Send className="w-4 h-4" />
                    {sendingNotif ? 'Enviando...' : 'Enviar notificación'}
                  </button>
                </div>
              )}
            </div>
          ))}
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
