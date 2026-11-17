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
    // Isolated state: the browser suite must never touch a running app's runs or approvals.
    env: {
      VENTURELAB_STATE_DIR: "../../.pytest_cache/ui-state",
      VENTURELAB_OUTPUT_DIR: "../../.pytest_cache/ui-outputs",
      VENTURELAB_DECISION_LOG: "../../.pytest_cache/ui-decision_log.json",
      OLLAMA_BASE_URL: "http://127.0.0.1:9",
    },
    timeout: 30000,
  },
});
