import { test, expect } from "@playwright/test";

test("ダッシュボードが起動し、予測ランキングが表示されること", async ({
  page,
}) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "BOATRACE=LOVE" }),
  ).toBeVisible();
  await expect(page.getByText("Prediction Board")).toBeVisible();
  await expect(page.getByText("Model Contract")).toBeVisible();
  await expect(page.getByLabel("Race ID")).toHaveValue("20260528_01_01");
  await expect(page.getByText("boatrace-love-api")).toBeVisible({
    timeout: 10000,
  });
  await expect(page.getByText("connected")).toBeVisible();
  await expect(
    page.getByRole("complementary").getByText("lgbm_win_v1"),
  ).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(6);
  await expect(page.getByText("Prob. sum")).toBeVisible();
});
