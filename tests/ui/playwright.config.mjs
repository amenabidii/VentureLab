import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.mjs",
  workers: 1,
  reporter: "list",
  outputDir: "../../.pytest_cache/ui-results",
  use: {
    baseURL: "http://127.0.0.1:8765",
    channel: process.env.UI_BROWSER || "msedge",
    headless: true,
  },
  webServer: {
    command:
      "..\\..\\.venv\\Scripts\\python -m uvicorn app.main:app --app-dir ../.. --host 127.0.0.1 --port 8765",
    url: "http://127.0.0.1:8765/health",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
