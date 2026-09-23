import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5173",
    headless: true,
    screenshot: "only-on-failure",
    viewport: { width: 1440, height: 1000 },
  },
  timeout: 60000,
});
