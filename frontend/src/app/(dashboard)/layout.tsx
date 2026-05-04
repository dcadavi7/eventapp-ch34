"use client";

import React, { ReactNode } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { useAuth } from '@/providers/AuthProvider';
import { redirect } from 'next/navigation';

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const { isAuthenticated, user } = useAuth();

  // Basic protection
  if (!isAuthenticated) {
    redirect('/auth/login');
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar role={user?.role || 'asistente'} />
      <main className="flex-1 overflow-auto p-8">
        {children}
      </main>
    </div>
  );
}
