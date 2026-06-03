import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("pmo_tour_done", "1");
    localStorage.setItem("pmo_token", "change-me-pmo-secret-2026");
  });
  await page.route("**/api/pmo/risk/**", async (route) => {
    await route.fulfill({
      json: {
        status: "success",
        project_risks: [
          {
            risk_title: "تأخیر",
            severity: "High",
            evidence: "گزارش",
            recommended_action: "اخطار",
          },
        ],
        htmlReport: "<html><body>risk</body></html>",
      },
    });
  });
});

test("risk run shows table", async ({ page }) => {
  await page.goto("/#risk");
  await page.click("#btnRisk");
  await expect(page.locator("#outRisk table")).toBeVisible();
});
