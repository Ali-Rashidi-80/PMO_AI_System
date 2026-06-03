import { defineConfig } from "@playwright/test";

/** Uses system Google Chrome (`channel: "chrome"`) — no bundled Chromium download. */
export default defineConfig({
  testDir: "./specs",
  timeout: 60000,
  use: {
    baseURL: "http://localhost:8080",
    locale: "fa-IR",
  },
  projects: [
    {
      name: "chrome",
      use: {
        channel: "chrome",
      },
    },
  ],
});
