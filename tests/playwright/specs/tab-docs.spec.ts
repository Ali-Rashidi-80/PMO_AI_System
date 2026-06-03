import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("pmo_tour_done", "1");
    localStorage.setItem("pmo_token", "change-me-pmo-secret-2026");
  });
  await page.route("**/api/pmo/documents/**", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        json: { status: "success", files: [], last_ingest_at: null },
      });
      return;
    }
    await route.continue();
  });
  await page.route("**/api/pmo/ingest**", async (route) => {
    await route.fulfill({
      json: { status: "success", chunks: 5, files: 2, count: 5 },
    });
  });
  await page.route("**/api/pmo/status**", async (route) => {
    await route.fulfill({
      json: { ready: true, dashboard: { lmstudio: "up", qdrant: "up", n8n: "up" } },
    });
  });
});

test("docs ingest button", async ({ page }) => {
  await page.goto("/#docs");
  await page.click("#btnIngest");
  await expect(page.locator("#ingestResult")).toBeVisible();
});

test("docs drop zone visible", async ({ page }) => {
  await page.goto("/#docs");
  await expect(page.locator("#dropZone")).toBeVisible();
});

test("docs upload mock", async ({ page }) => {
  await page.route("**/api/pmo/documents/upload**", async (route) => {
    await route.fulfill({
      json: {
        status: "success",
        saved: 1,
        skipped: 0,
        files: [{ name: "test.txt", status: "saved", chunks: 0 }],
      },
    });
  });
  await page.goto("/#docs");
  await page.setInputFiles("#fileInput", {
    name: "test.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("بند قرارداد تأخیر جریمه. ".repeat(5)),
  });
  await expect(page.locator("#uploadProgress")).toBeHidden({ timeout: 10000 });
});
