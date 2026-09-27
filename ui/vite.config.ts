import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Build output is static files (dist/) — deploy straight to an S3 bucket configured
// for static website hosting, or behind CloudFront. No Node server needed in prod.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // floci (local Cognito emulator) doesn't send CORS headers, so a direct browser
      // fetch to it fails preflight with an opaque "Failed to fetch". Real AWS Cognito's
      // public InitiateAuth endpoint does support CORS, so this proxy only exists for
      // local dev against floci — set VITE_COGNITO_ENDPOINT_URL=/cognito-idp to use it.
      "/cognito-idp": {
        target: "http://localhost:4566",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/cognito-idp/, ""),
      },
    },
  },
});
