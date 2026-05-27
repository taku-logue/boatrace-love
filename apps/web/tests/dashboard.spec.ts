import { test, expect } from "@playwright/test";

test("ダッシュボードが起動し、APIとDBのステータスがokになること", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByText("BOATRACE=LOVE MVP Dashboard")).toBeVisible();
  await expect(page.getByText("API Status")).toBeVisible();
  await expect(page.getByText("Database Status")).toBeVisible();
  await expect(
    page.locator("pre").filter({ hasText: '"service": "boatrace-love-api"' }),
  ).toBeVisible({ timeout: 10000 });
  await expect(
    page.locator("pre").filter({ hasText: '"database": "connected"' }),
  ).toBeVisible();
});
