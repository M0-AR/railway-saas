import { expect, type Page } from "@playwright/test";

export async function login(
  page: Page,
  {
    slug = "demo",
    email = "demo@railway.demo",
    password = "demo1234",
  }: { slug?: string; email?: string; password?: string } = {},
) {
  await page.goto(`/login?tenant=${slug}`);
  await page.getByLabel("Workspace slug").fill(slug);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

export async function loginAsDemo(page: Page) {
  await login(page);
}
