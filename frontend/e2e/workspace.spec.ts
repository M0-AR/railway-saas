import { expect, test } from "@playwright/test";

import { login, loginAsDemo } from "./helpers";

test.describe("demo workspace", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsDemo(page);
  });

  test("lists the seeded fleet", async ({ page }) => {
    await page.goto("/trains");

    await expect(page.getByRole("heading", { level: 1, name: "Trains" })).toBeVisible();
    await expect(page.getByText("Showing 1–12 of 12")).toBeVisible();
    await expect(page.getByText("CG-880")).toBeVisible();
  });

  test("shows the seeded reservation ledger", async ({ page }) => {
    await page.goto("/bookings");

    await expect(page.getByRole("heading", { level: 1, name: "Bookings" })).toBeVisible();
    await expect(page.getByText("Showing 1–20 of 48")).toBeVisible();
  });

  test("renders growth analytics", async ({ page }) => {
    await page.goto("/reports");

    await expect(page.getByRole("heading", { level: 1, name: "Reports" })).toBeVisible();
    await expect(page.getByText("Advanced analytics is a Growth feature")).toHaveCount(0);
    await expect(page.getByText("Top trains")).toBeVisible();
  });

  test("records activity in the audit log", async ({ page }) => {
    await page.goto("/audit");

    await expect(page.getByRole("heading", { level: 1, name: "Audit log" })).toBeVisible();
    await expect(page.locator("tbody tr").first()).toBeVisible();
  });

  test("lists the seeded team", async ({ page }) => {
    await page.goto("/team");

    await expect(page.getByRole("heading", { level: 1, name: "Team" })).toBeVisible();
    await expect(page.getByText("demo@railway.demo")).toBeVisible();
    await expect(page.getByText("northline", { exact: false })).toHaveCount(0);
  });

  test("prefills branding in settings", async ({ page }) => {
    await page.goto("/settings");

    await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();
    await expect(page.getByLabel("Logo text")).toHaveValue("Demo Rail");
  });
});

test("starter workspaces see the upgrade gate", async ({ page }) => {
  await login(page, {
    slug: "starter",
    email: "owner@starter.demo",
    password: "demo1234",
  });

  await page.goto("/trains");
  await expect(page.getByText("Showing 1–2 of 2")).toBeVisible();

  await page.goto("/reports");
  await expect(page.getByRole("heading", { level: 1, name: "Reports" })).toBeVisible();
  await expect(page.getByText("Advanced analytics is a Growth feature")).toBeVisible();
  await expect(page.getByRole("link", { name: "Compare plans" })).toBeVisible();
});
