import { EventData } from '@/components/ui/EventCard';
import api from '@/lib/api';

export interface CreateEventPayload {
  name: string;
  startDate: string;
  endDate?: string;
  location?: string;
  organizerId: string;
  organizerEmail?: string;
  capacity: number;
  description?: string;
}

export interface UpdateEventPayload {
  name?: string;
  description?: string;
  status?: string;
  startDate?: string;
  location?: string;
  capacity?: number;
}

function mapApiEventToEventData(apiEvent: any): EventData {
  let dateStr = "Sin fecha";
  let timeStr = "Sin hora";
  let durationStr = "No especificada";

  if (apiEvent.startDate) {
    const start = new Date(apiEvent.startDate);
    dateStr = start.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    timeStr = start.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    
    if (apiEvent.endDate) {
      const end = new Date(apiEvent.endDate);
      const diffMs = end.getTime() - start.getTime();
      const diffHrs = Math.round(diffMs / (1000 * 60 * 60));
      durationStr = `${diffHrs} horas`;
    }
  }

  // Mapear status del backend ('PROGRAMADO', etc) al del frontend ('Activo', 'Cancelado', etc)
  let statusStr = apiEvent.status;
  if (statusStr === 'PROGRAMADO') {
    statusStr = 'Activo';
  } else if (statusStr === 'EN_CURSO') {
    statusStr = 'En curso';
  } else if (statusStr === 'FINALIZADO') {
    statusStr = 'Finalizado';
  } else if (statusStr === 'CANCELADO') {
    statusStr = 'Cancelado';
  }

  const capacity = Number(apiEvent.capacity) || 0;
  const available = Number(apiEvent.availableCapacity) || 0;

  return {
    id: apiEvent.id || (apiEvent.PK ? apiEvent.PK.replace('EVENT#', '') : ''),
    name: apiEvent.name || 'Sin nombre',
    description: apiEvent.description || 'Sin descripción',
    date: dateStr,
    time: timeStr,
    duration: durationStr,
    capacity: capacity,
    registered: capacity - available,
    status: statusStr as any,
    location: apiEvent.location || 'Virtual'
  };
}

export const eventService = {
  // GET /events?includeAll=true — todos los estados (vista organizador)
  async getAllEventos(): Promise<EventData[]> {
    try {
      const response = await api.get('/events?includeAll=true');
      return response.data.map(mapApiEventToEventData);
    } catch (error) {
      console.error('Error fetching all events:', error);
      throw error;
    }
  },

  // GET /events — solo PROGRAMADO (backend filtra por GSI, vista asistente)
  async getEventosActivos(): Promise<EventData[]> {
    try {
      const response = await api.get('/events');
      return response.data.map(mapApiEventToEventData);
    } catch (error) {
      console.error('Error fetching active events:', error);
      throw error;
    }
  },

  // GET /events?registered=true
  async getMisEventosRegistrados(): Promise<EventData[]> {
    try {
      const response = await api.get('/events?registered=true');
      return response.data.map(mapApiEventToEventData);
    } catch (error) {
      console.error('Error fetching registered events:', error);
      throw error;
    }
  },

  // GET /events/{id}
  async getEventById(id: string): Promise<EventData> {
    try {
      const response = await api.get(`/events/${id}`);
      return mapApiEventToEventData(response.data);
    } catch (error) {
      console.error('Error fetching event by id:', error);
      throw error;
    }
  },

  // POST /events
  async createEvent(payload: CreateEventPayload): Promise<any> {
    try {
      const response = await api.post('/events', payload);
      return response.data;
    } catch (error) {
      console.error('Error creating event:', error);
      throw error;
    }
  },

  // PUT /events/{id}
  async updateEvent(id: string, payload: UpdateEventPayload): Promise<any> {
    try {
      const response = await api.put(`/events/${id}`, payload);
      return response.data;
    } catch (error) {
      console.error('Error updating event:', error);
      throw error;
    }
  },

  // DELETE /events/{id}
  async deleteEvent(id: string): Promise<any> {
    try {
      const response = await api.delete(`/events/${id}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting event:', error);
      throw error;
    }
  },

  // POST /events/{id}/reports
  async requestReport(eventId: string, requesterEmail: string): Promise<any> {
    try {
      const response = await api.post(`/events/${eventId}/reports`, { requesterEmail });
      return response.data;
    } catch (error) {
      console.error('Error requesting report:', error);
      throw error;
    }
  },

  // POST /events/{id}/notifications
  async sendNotification(eventId: string, subject: string, message: string): Promise<any> {
    try {
      const response = await api.post(`/events/${eventId}/notifications`, { subject, message });
      return response.data;
    } catch (error) {
      console.error('Error sending mass notification:', error);
      throw error;
    }
  },

  // POST /registrations
  async registerToEvent(payload: { eventId: string, userId: string, name: string, email: string }): Promise<any> {
    try {
      const response = await api.post('/registrations', payload);
      return response.data;
    } catch (error) {
      console.error('Error registering to event:', error);
      throw error;
    }
  }
};
