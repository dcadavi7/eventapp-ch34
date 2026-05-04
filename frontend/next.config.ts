import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Exportación estática para desplegar en S3 + CloudFront sin servidor Node.js
  output: 'export',

  // Genera index.html dentro de cada carpeta (ej: /about/ → /about/index.html)
  // Necesario para que CloudFront resuelva rutas correctamente desde S3
  trailingSlash: true,

  // La optimización de imágenes de Next.js requiere un servidor; la deshabilitamos
  // para que la exportación estática funcione sin errores de build
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
