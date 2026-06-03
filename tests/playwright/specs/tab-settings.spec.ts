import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("pmo_tour_done", "1");
    localStorage.setItem("pmo_token", "change-me-pmo-secret-2026");
  });
  await page.route("**/api/pmo/status**", async (route) => {
    await route.fulfill({
      json: {
        ready: true,
        documents_count: 2,
        last_ingest_at: "2026-06-02T12:00:00Z",
        dashboard: { lmstudio: "up", qdrant: "up", n8n: "up", llm_model: "gemma", embed_model: "nomic-embed-text-v2" },
      },
    });
  });
});

test("settings status cards", async ({ page }) => {
  await page.goto("/#settings");
  await expect(page.locator("#lmStatus")).toContainText(/gemma|آنلاین/i);
  await expect(page.locator("#qdStatus")).toContainText(/2 سند|سند/);
});

test("theme toggle", async ({ page }) => {
  await page.goto("/#settings");
  await page.click("#btnTheme");
  const theme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  expect(theme).toBeTruthy();
});
