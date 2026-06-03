import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("pmo_tour_done", "1");
    localStorage.setItem("pmo_token", "change-me-pmo-secret-2026");
  });
  await page.route("**/api/pmo/letter**", async (route) => {
    await route.fulfill({
      json: { status: "success", letter: "نامه mock" },
    });
  });
});

test("letter validation empty", async ({ page }) => {
  await page.goto("/#letter");
  await page.click("#btnLetter");
  await expect(page.locator("#errLetter")).toBeVisible();
});

test("letter free prompt", async ({ page }) => {
  await page.goto("/#letter");
  await page.locator("#panel-letter details.pro-panel summary").click();
  await page.fill("#letterFree", "نامه آزاد");
  await page.click("#btnLetter");
  await expect(page.locator("#outLetter")).toContainText("mock");
});
