import { defineConfig } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(frontendRoot, "..");
const localPython = path.join(repositoryRoot, ".venv", "Scripts", "python.exe");
const python = process.env.CI ? "python" : `"${process.env.PYTHON || localPython}"`;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "recall-workflow.spec.ts",
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    channel: process.env.CI ? undefined : "msedge",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `${python} -m uvicorn backend.app:app --host 127.0.0.1 --port 8000`,
      cwd: repositoryRoot,
      env: { RECALLNEXT_DATA_SOURCE: "SYNTHETIC_FIXTURE" },
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
      timeout: 120_000,
      name: "fixture-api",
    },
    {
      command: "pnpm dev --host 127.0.0.1 --port 5174 --strictPort",
      cwd: frontendRoot,
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      timeout: 120_000,
      name: "frontend",
    },
  ],
});
