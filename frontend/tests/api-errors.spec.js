import { test, expect } from "@playwright/test";

for (const [status, body, message] of [
  [500, "Internal Server Error", "backend is unavailable (HTTP 500)"],
  [404, "<html>Not found</html>", "API route is unavailable"],
  [200, "<html>SPA fallback</html>", "API route is unavailable"],
]) {
  test(`login handles a non-JSON HTTP ${status} response`, async ({ page }) => {
    await page.route("**/api/admin/login", (route) =>
      route.fulfill({ status, contentType: "text/html", body }),
    );
    await page.goto("/admin");
    await page.getByLabel("Username", { exact: true }).fill("admin123");
    await page.getByLabel("Password", { exact: true }).fill("admin@123");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText(message);
    await expect(page).toHaveURL(/\/admin$/);
  });
}
