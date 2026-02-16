import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Accessible depuis le reseau (pas seulement localhost)
    port: 5173,
  },
});
