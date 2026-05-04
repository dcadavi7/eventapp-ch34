"use client";

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Save, ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { eventService } from '@/services/eventService';

export default function CrearEventoPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editId = searchParams.get('edit');
  
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    date: '',
    time: '',
    duration: '',
    capacity: 0,
    location: ''
  });

  useEffect(() => {
    if (editId) {
      const fetchEvent = async () => {
        try {
          setFetching(true);
          const event = await eventService.getEventById(editId);
          
          // El backend nos devuelve la fecha en formato ISO, hay que separarla para los inputs
          // Nota: mapApiEventToEventData ya nos da 'date' (DD/MM/YYYY) y 'time' (HH:mm)
          // Pero los inputs tipo date esperan YYYY-MM-DD
          
          // Re-formatear date para input type="date" (YYYY-MM-DD)
          // Como ya tenemos el objeto Date en el mapeador, tal vez sea mejor pedir el raw o parsear de nuevo
          // Por simplicidad, parseamos el 'date' que viene (DD/MM/YYYY)
          const [day, month, year] = event.date.split('/');
          const formattedDate = `${year}-${month}-${day}`;

          setFormData({
            name: event.name,
            description: event.description,
            date: formattedDate,
            time: event.time,
            duration: event.duration,
            capacity: event.capacity,
            location: event.location || ''
          });
        } catch (error) {
          console.error("Error fetching event for edit", error);
          alert("No se pudo cargar la información del evento.");
        } finally {
          setFetching(false);
        }
      };
      fetchEvent();
    }
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const eventDate = new Date(`${formData.date}T${formData.time}`);
    const now = new Date();
    
    // Solo validar fecha futura si es creación? 
    // O permitir editar eventos pasados? Generalmente se valida.
    if (!editId && eventDate < now) {
      alert("La fecha del evento debe ser en el futuro.");
      return;
    }

    try {
      setLoading(true);
      const startDate = eventDate.toISOString();
      
      const payload = {
        name: formData.name,
        startDate: startDate,
        description: formData.description,
        capacity: Number(formData.capacity),
        location: formData.location,
        organizerId: 'org-demo',
      };

      if (editId) {
        await eventService.updateEvent(editId, payload);
        alert("Evento actualizado exitosamente");
      } else {
        await eventService.createEvent(payload);
        alert("Evento creado exitosamente");
      }
      
      router.push('/organizador/dashboard');
    } catch (error) {
      console.error("Error saving event", error);
      alert(`Ocurrió un error al ${editId ? 'actualizar' : 'crear'} el evento.`);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-8">
        <Link 
          href="/organizador/dashboard" 
          className="p-2 bg-white rounded-full border border-slate-200 hover:bg-slate-50 transition"
        >
          <ArrowLeft className="w-5 h-5 text-slate-600" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-brand-900">
            {editId ? 'Editar Evento' : 'Crear Nuevo Evento'}
          </h1>
          <p className="text-slate-600 mt-1">
            {editId ? 'Modifica los detalles del evento seleccionado.' : 'Configura los detalles del espacio académico o institucional.'}
          </p>
        </div>
      </div>

      {fetching ? (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 flex justify-center items-center">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
            <p className="text-slate-500 animate-pulse">Cargando detalles del evento...</p>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">Nombre del Evento</label>
              <input
                type="text"
                name="name"
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                value={formData.name}
                onChange={handleChange}
                placeholder="Ej. Seminario Internacional de Tecnología"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">Descripción</label>
              <textarea
                name="description"
                required
                rows={4}
                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
                value={formData.description}
                onChange={handleChange}
                placeholder="Detalle de las actividades y objetivos..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fecha</label>
              <input
                type="date"
                name="date"
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                value={formData.date}
                onChange={handleChange}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Hora de Inicio</label>
              <input
                type="time"
                name="time"
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                value={formData.time}
                onChange={handleChange}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Duración Aproximada</label>
              <input
                type="text"
                name="duration"
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                value={formData.duration}
                onChange={handleChange}
                placeholder="Ej. 2 horas"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Capacidad Máxima de Asistentes</label>
              <input
                type="number"
                name="capacity"
                required
                min="0"
                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                value={formData.capacity || ''}
                onChange={handleChange}
                placeholder="0"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">Ubicación / Modalidad</label>
              <input
                type="text"
                name="location"
                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                value={formData.location}
                onChange={handleChange}
                placeholder="Auditorio X / Virtual (Enlace)"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex justify-end gap-3">
            <Link 
              href="/organizador/dashboard"
              className="py-2 px-4 border border-slate-300 rounded-md shadow-sm text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 focus:outline-none"
            >
              Cancelar
            </Link>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 py-2 px-6 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 focus:outline-none disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {loading ? 'Guardando...' : 'Guardar Evento'}
            </button>
          </div>
        </form>
      </div>
      )}
    </div>
  );
}
