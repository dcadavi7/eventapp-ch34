import { redirect } from 'next/navigation';

export default function HomePage() {
  // Redirigir siempre al login ya que la aplicación requiere autenticación
  redirect('/auth/login');
}
