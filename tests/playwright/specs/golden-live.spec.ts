import { test, expect } from "@playwright/test";

const live = process.env.PMO_LIVE === "1";

test.describe("golden live @golden", () => {
  test.skip(!live, "Set PMO_LIVE=1 and ensure LM Studio + stack are running");

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("pmo_tour_done", "1");
      localStorage.setItem("pmo_token", "change-me-pmo-secret-2026");
    });
  });

  test("chat golden — structural response", async ({ page }) => {
    test.setTimeout(300_000);
    await page.goto("/#chat");
    await page.fill("#chatPrompt", "یک جمله کوتاه درباره PMO بنویس.");
    await page.click("#btnChat");
    await expect(page.locator("#outChat")).not.toHaveClass(/empty-state/, {
      timeout: 300_000,
    });
    const text = await page.locator("#outChat").innerText();
    expect(text.length).toBeGreaterThan(5);
  });

  test("letter golden — output present", async ({ page }) => {
    test.setTimeout(300_000);
    await page.goto("/#letter");
    await page.locator("#panel-letter details.pro-panel summary").click();
    await page.fill("#letterFree", "نامه کوتاه تست golden");
    await page.click("#btnLetter");
    await expect(page.locator("#outLetter")).not.toHaveClass(/empty-state/, {
      timeout: 300_000,
    });
  });
});
