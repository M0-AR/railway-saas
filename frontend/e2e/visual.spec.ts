import { expect, test } from "@playwright/test";

import { loginAsDemo } from "./helpers";

/*
 * Visual regression is opt-in (E2E_VISUAL=1) so local font/AA differences do
 * not make the default suite flaky. Baselines live next to this file and are
 * refreshed with:  E2E_VISUAL=1 npx playwright test visual --update-snapshots
 */
const enabled = process.env.E2E_VISUAL === "1";

test.describe("visual regression", () => {
  test.skip(!enabled, "Set E2E_VISUAL=1 to run visual snapshots");

  test("login page", async ({ page }) => {
    await page.goto("/login?tenant=demo");
    await expect(page.getByText("Signing in to Demo Rail Co · growth plan")).toHaveCount(1);

    await expect(page).toHaveScreenshot("login.png", {
      maxDiffPixelRatio: 0.02,
      fullPage: true,
    });
  });

  test("trains workspace", async ({ page }) => {
    await loginAsDemo(page);
    await page.goto("/trains");
    await expect(page.getByText("Showing 1–12 of 12")).toBeVisible();

    await expect(page).toHaveScreenshot("trains.png", {
      maxDiffPixelRatio: 0.02,
      fullPage: true,
    });
  });
});
