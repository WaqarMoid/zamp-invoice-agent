import { test, expect } from "@playwright/test";

test.describe("AP Invoice Desk Smoke Tests", () => {
  test("processes F01 to Approved and shows on dashboard", async ({ page }) => {
    // 1. Open /new
    await page.goto("/new");
    await expect(page.locator("h1")).toContainText("Process invoice");

    // 2. Find F01 card and click Run
    const f01Card = page.locator("div").filter({ hasText: "Classic single-page tax invoice" }).first();
    const runButton = f01Card.locator("button", { hasText: "Run" });
    await runButton.click();

    // 3. Wait for redirect to /runs/:id
    await expect(page).toHaveURL(/\/runs\//);

    // 4. Wait for Approved text on run page
    await expect(page.locator("text=Approved").first()).toBeVisible({ timeout: 60000 });

    // 5. Navigate to Dashboard /
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Invoices");
    await expect(page.locator("text=Sharma Packaging Solutions").first()).toBeVisible();
  });

  test("processes F05 to On hold with security callout", async ({ page }) => {
    await page.goto("/new");

    // Find F05 card and click Run
    const f05Card = page.locator("div").filter({ hasText: "Bank account change alert" }).first();
    const runButton = f05Card.locator("button", { hasText: "Run" });
    await runButton.click();

    await expect(page).toHaveURL(/\/runs\//);

    // Wait for On hold text and Security Protocol callout
    await expect(page.locator("text=On hold").first()).toBeVisible({ timeout: 60000 });
    await expect(
      page.locator("text=Do not reply to the email this invoice came from")
    ).toBeVisible({ timeout: 30000 });
  });
});
