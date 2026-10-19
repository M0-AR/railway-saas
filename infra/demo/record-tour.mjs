#!/usr/bin/env node
/**
 * Records the RailFlow product tour used for docs/assets/gifs/tour.gif.
 *
 * Usage (from the repo root, with the demo stack running):
 *   node infra/demo/record-tour.mjs
 *
 * Then convert the printed .webm path with ffmpeg, e.g.:
 *   ffmpeg -y -i out/<video>.webm \
 *     -vf "fps=12,scale=1200:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer" \
 *     docs/assets/gifs/tour.gif
 */
import { createRequire } from "node:module";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(here, "../../frontend/package.json"));
const { chromium } = require("playwright");

const baseUrl = process.env.E2E_BASE_URL ?? "http://demo.localhost:8095";
const outDir = process.env.TOUR_VIDEO_DIR ?? path.join(here, "out");

fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: outDir, size: { width: 1280, height: 720 } },
});
const page = await context.newPage();
page.setDefaultTimeout(20_000);

const pause = (ms) => page.waitForTimeout(ms);

await page.goto(`${baseUrl}/login?tenant=demo`);
await pause(700);
await page.getByLabel("Workspace slug").fill("demo");
await page.getByLabel("Email").fill("demo@railway.demo");
await page.getByLabel("Password").fill("demo1234");
await pause(600);
await page.getByRole("button", { name: /sign in/i }).click();
await page.waitForURL(/\/dashboard/);
await pause(2600);

await page.getByRole("link", { name: "Bookings" }).click();
await page.waitForURL(/\/bookings/);
await page.locator("tbody tr").first().waitFor();
await pause(2200);

await page.locator("tbody tr").first().click();
await page.getByRole("dialog").waitFor();
await pause(2600);
await page.keyboard.press("Escape");
await pause(400);

await page.getByRole("link", { name: "Trains" }).click();
await page.waitForURL(/\/trains/);
await pause(2200);

await page.getByRole("link", { name: "Reports" }).click();
await page.waitForURL(/\/reports/);
await pause(2600);

const video = page.video();
await page.close();
await context.close();
await browser.close();

const videoPath = await video.path();
console.log(videoPath);
