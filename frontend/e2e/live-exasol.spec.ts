import { expect, test } from "@playwright/test";

test("visible application reports a live Exasol data source", async ({ page }) => {
  const healthResponse = await page.request.get("/api/health");
  expect(healthResponse.ok()).toBeTruthy();
  await expect(healthResponse.json()).resolves.toMatchObject({
    status: "ok",
    data_source: "EXASOL_PERSONAL",
    database_connected: true,
  });

  await page.goto("/");
  await expect(page.getByText("EXASOL PERSONAL", { exact: true })).toBeVisible();
  await expect(page.getByText("Official public recall context", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Shipment exposure" })).toBeVisible();
  await expect(page.getByText("synthetic private warehouse fixture", { exact: false })).toBeVisible();
});
