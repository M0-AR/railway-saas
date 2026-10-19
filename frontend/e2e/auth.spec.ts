import { expect, test } from "@playwright/test";

import { loginAsDemo } from "./helpers";

test("anonymous visitors are sent to login with a next hop", async ({ page }) => {
  await page.goto("/trains");

  await expect(page).toHaveURL(/\/login\?next=/);
  await expect(page.getByRole("heading", { name: "Sign in to your workspace" })).toBeVisible();
});

test("login page resolves the demo workspace branding", async ({ page }) => {
  await page.goto("/login?tenant=demo");

  await expect(page.getByText("Signing in to Demo Rail Co · growth plan")).toHaveCount(1);
});

test("bad credentials show a single inline error", async ({ page }) => {
  await page.goto("/login?tenant=demo");
  await page.getByLabel("Workspace slug").fill("demo");
  await page.getByLabel("Email").fill("demo@railway.demo");
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: /sign in/i }).click();

  await expect(page.getByText("Invalid email or password.")).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test("demo credentials land on the dashboard", async ({ page }) => {
  await loginAsDemo(page);

  await expect(page.getByRole("heading", { level: 1, name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Revenue · 30 days")).toBeVisible();
  await expect(page.getByText("Occupancy today")).toBeVisible();
});
