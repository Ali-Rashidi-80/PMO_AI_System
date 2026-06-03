import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("pmo_tour_done", "1");
    localStorage.setItem("pmo_token", "change-me-pmo-secret-2026");
  });
  await page.route("**/api/pmo/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/chat/stream")) {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: 'data: {"delta":"سلام"}\n\ndata: {"done":true,"used_rag":false}\n\n',
      });
      return;
    }
    if (url.includes("/chat")) {
      await route.fulfill({
        json: { status: "success", output: "پاسخ mock", used_rag: false },
      });
      return;
    }
    if (url.includes("/status")) {
      await route.fulfill({
        json: {
          ready: true,
          documents_count: 1,
          dashboard: { lmstudio: "up", qdrant: "up", n8n: "up" },
        },
      });
      return;
    }
    await route.continue();
  });
});

test("chat empty validation", async ({ page }) => {
  await page.goto("/#chat");
  await page.click("#btnChat");
  await expect(page.locator("#errChat")).toBeVisible();
});

test("chat stream mock", async ({ page }) => {
  await page.goto("/#chat");
  await page.fill("#chatPrompt", "سلام");
  await page.click("#btnChat");
  await expect(page.locator("#outChat")).toContainText("سلام");
});
