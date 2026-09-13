import { expect, test } from "@playwright/test";

test("review, accept and retract evidence through the browser", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Shipment exposure" })).toBeVisible();
  await expect(page.getByText("SYNTHETIC FIXTURE", { exact: true })).toBeVisible();
  await expect(page.getByText("6 shipments", { exact: true })).toBeVisible();
  await expect(page.getByText("125", { exact: true })).toBeVisible();

  await expect(page.getByLabel("Source reference")).not.toHaveValue("");
  await page.getByRole("button", { name: "Save proposal" }).click();
  await expect(page.getByText("Proposal saved. Decisions have not changed.")).toBeVisible();

  await page.getByLabel("Verified by").fill("Browser test reviewer");
  await page.getByRole("button", { name: "Accept and reassess" }).click();
  await expect(page.getByText("Active investigation - version 2")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Decision changes" })).toBeVisible();

  await page.getByLabel("Retraction reason").fill("Automated retraction check");
  await page.getByRole("button", { name: "Retract latest reviewed evidence" }).click();
  await expect(page.getByText("Active investigation - version 3")).toBeVisible();
  await expect(page.getByText("Evidence retracted into incident version 3.")).toBeVisible();
});
