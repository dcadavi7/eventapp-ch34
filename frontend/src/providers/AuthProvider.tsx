"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';

export type UserRole = 'organizador' | 'asistente' | null;

interface UserProfile {
  name: string;
  email: string;
  role: UserRole;
  id?: string;
}

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  login: (email: string, role: UserRole) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<UserProfile | null>(null);

  // Simulando chequeo de la sesión de Cognito JWT
  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('cognito_access_token') : null;
    const role = typeof window !== 'undefined' ? localStorage.getItem('cognito_role') as UserRole : null;
    const email = typeof window !== 'undefined' ? localStorage.getItem('cognito_email') || '' : '';
    if (token && role) {
      setUser({ name: email.split('@')[0] || 'Usuario', email, role });
    }
  }, []);

  const login = (email: string, role: UserRole) => {
    setUser({ name: email.split('@')[0], email, role });
    localStorage.setItem('cognito_access_token', 'mock_jwt_token_12345');
    localStorage.setItem('cognito_role', role || 'asistente');
    localStorage.setItem('cognito_email', email);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('cognito_access_token');
    localStorage.removeItem('cognito_role');
    localStorage.removeItem('cognito_email');
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider');
  }
  return context;
};
