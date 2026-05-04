import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Calendar, LayoutDashboard, UserCircle, LogOut } from 'lucide-react';
import { cn } from '@/lib/utils';
import { UserRole, useAuth } from '@/providers/AuthProvider';

export const Sidebar = ({ role }: { role: UserRole }) => {
  const pathname = usePathname();
  const { logout } = useAuth();
  
  const navItems = [
    ...(role === 'organizador' ? [
      { name: 'Dashboard', href: '/organizador/dashboard', icon: LayoutDashboard },
    ] : []),
    { name: 'Lista de eventos', href: '/asistente/eventos', icon: Calendar },
    { name: 'Mi Perfil', href: '/asistente/perfil', icon: UserCircle },
  ];

  return (
    <div className="w-64 bg-white border-r border-slate-200 shadow-sm flex flex-col justify-between h-full">
      <div>
        <div className="p-6">
          <h2 className="text-2xl font-bold tracking-tight text-brand-900">TicketEvents</h2>
          <p className="text-sm text-slate-500 mt-1">Portal {role === 'organizador' ? 'Organizador' : 'Universitario'}</p>
        </div>
        
        <nav className="px-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                  isActive 
                    ? "bg-brand-50 text-brand-700" 
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                <item.icon className={cn("w-5 h-5", isActive ? "text-brand-600" : "text-slate-400")} />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-slate-200">
        <button 
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 w-full text-sm font-medium text-slate-600 rounded-md hover:bg-red-50 hover:text-red-700 transition-colors"
        >
          <LogOut className="w-5 h-5 text-slate-400" />
          Cerrar Sesión
        </button>
      </div>
    </div>
  );
};
