import axios from 'axios';

// Instancia de API configurada para conectarse a API Gateway
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'https://api.gateway.mock.aws.com/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para inyectar token JWT de Cognito
api.interceptors.request.use((config) => {
  // En un escenario real, aquí se obtiene la sesión actual usando Cognito/Amplify
  const token = typeof window !== 'undefined' ? localStorage.getItem('cognito_access_token') : null;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default api;
