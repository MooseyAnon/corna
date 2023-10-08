import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import legacy from '@vitejs/plugin-legacy'
import vue2 from '@vitejs/plugin-vue2'
import path from "path";

// configure address and post for backend system
let HOST = "127.0.0.1";
let LOCAL_CORNA_SERVER = `${HOST}:8080/api/v1`
// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue2(),
    legacy({
      targets: ['ie >= 11'],
      additionalLegacyPolyfills: ['regenerator-runtime/runtime']
    })
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    }
  },
  server: {
    host: HOST,
    proxy: {
      "https://api.mycorna.com/v1/*": LOCAL_CORNA_SERVER,
      "*/corna/*": LOCAL_CORNA_SERVER,
    },
  },
})
