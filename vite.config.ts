import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  // public/data holds ~15k generated files: never watch or scan them
  server: { port: 5173, watch: { ignored: ['**/public/data/**', '**/data/**', '**/.venv/**'] } },
  optimizeDeps: { entries: ['index.html'] },
  build: { chunkSizeWarningLimit: 1500 },
});
