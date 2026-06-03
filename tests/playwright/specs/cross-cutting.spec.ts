import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("pmo_tour_done", "1"));
});

test("hash ingest maps to docs", async ({ page }) => {
  await page.goto("/#ingest");
  await expect(page.locator("#panel-docs")).toHaveClass(/active/);
});

test("rtl direction", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
});
