import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { loginAsDemo } from "./helpers";

async function expectNoSeriousViolations(page: import("@playwright/test").Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );
  expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
}

test("login page has no serious accessibility violations", async ({ page }) => {
  await page.goto("/login?tenant=demo");
  await expect(page.getByRole("heading", { name: "Sign in to your workspace" })).toBeVisible();

  await expectNoSeriousViolations(page);
});

test("core workspace pages have no serious accessibility violations", async ({ page }) => {
  await loginAsDemo(page);

  for (const path of ["/dashboard", "/trains", "/bookings", "/reports"]) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    await expectNoSeriousViolations(page);
  }
});
