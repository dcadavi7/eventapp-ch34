# Sistema de Gestión de Eventos - Frontend

Este es el frontend de la aplicación de gestión de eventos, construido con [Next.js 14+](https://nextjs.org/) y Tailwind CSS. La aplicación está integrada con una infraestructura serverless en AWS (Lambda, API Gateway, DynamoDB).

## Características principales

- **Panel de Organizador:** Crear, editar, gestionar estados (Activo, En curso, Finalizado) y eliminar eventos.
- **Vista de Asistente:** Catálogo de eventos disponibles y registro a eventos.
- **Integración con AWS:** Comunicación directa con API Gateway y persistencia en DynamoDB.

## Requisitos Previos

- [Node.js](https://nodejs.org/) (versión 18 o superior recomendada)
- [npm](https://www.npmjs.com/) o [yarn](https://yarnpkg.com/)

## Configuración del Entorno

Para que el frontend pueda comunicarse con el backend en AWS, es necesario configurar la URL de la API.

1. En la raíz del directorio `events-app`, crea un archivo llamado `.env.local` (si no existe).
2. Agrega la siguiente variable con la URL de tu API Gateway:

```env
NEXT_PUBLIC_API_GATEWAY_URL=https://tu-id-api.execute-api.us-west-1.amazonaws.com/lab
```

> **Nota:** Asegúrate de incluir el stage (ej. `/lab` o `/prod`) al final de la URL.

## Ejecución en Local

Una vez configurado el entorno, instala las dependencias y ejecuta el servidor de desarrollo:

```bash
# Instalar dependencias
npm install

# Ejecutar el servidor de desarrollo
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000) en tu navegador para ver la aplicación.

## Scripts Disponibles

- `npm run dev`: Ejecuta la aplicación en modo desarrollo.
- `npm run build`: Genera la versión de producción de la aplicación.
- `npm run start`: Inicia la aplicación en modo producción (requiere build previo).
- `npm run lint`: Ejecuta el linter para revisar la calidad del código.

## Tecnologías Utilizadas

- **Framework:** Next.js (App Router)
- **Estilos:** Tailwind CSS
- **Iconos:** Lucide React
- **Cliente API:** Axios
