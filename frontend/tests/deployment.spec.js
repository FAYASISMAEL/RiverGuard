import { test, expect } from "@playwright/test";
test.skip(
  !process.env.VERCEL_SIMULATION,
  "Run against the built SPA deployment simulator.",
);

test("production routes and river layers survive navigation and refresh without DB", async ({
  page,
}) => {
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    for (const path of ["/", "/map", "/report", "/history", "/admin"]) {
      const response = await page.goto(path);
      expect(response.status()).toBe(200);
      await expect(page.locator("main")).toBeVisible();
      await page.reload();
      await expect(page.locator("main")).toBeVisible();
      if (path === "/map") {
        await expect(
          page.locator("path[data-segment-id]").first(),
        ).toBeAttached();
        expect(
          (await page.locator(".river-map").boundingBox()).height,
        ).toBeGreaterThan(250);
      }
    }
  }
});

test("degraded API gives JSON and database-independent analysis", async ({
  request,
  page,
}) => {
  const health = await (await request.get("/api/health")).json();
  expect(health).toMatchObject({
    status: "degraded",
    map: "available",
    database: "unavailable",
  });
  for (const layer of [
    "river",
    "settlements",
    "intakes",
    "monitoring-points",
    "local-bodies",
  ]) {
    const response = await request.get("/api/map/" + layer);
    expect(response.ok()).toBe(true);
    expect((await response.json()).type).toBe("FeatureCollection");
  }
  const analysis = await request.post("/api/analyze", {
    data: { latitude: 10.1200287, longitude: 76.379479 },
  });
  expect(analysis.ok()).toBe(true);
  expect((await analysis.json()).repeat_history_available).toBe(false);
  await page.goto("/admin");
  await page.getByLabel("Username", { exact: true }).fill("admin123");
  await page.getByLabel("Password", { exact: true }).fill("admin@123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Database unavailable");
});

test("map retries a temporary layer error and recovers", async ({ page }) => {
  let attempts = 0;
  await page.route("**/api/map/river", (route) => {
    attempts++;
    return attempts === 1
      ? route.fulfill({
          status: 503,
          json: { detail: "Temporarily unavailable" },
        })
      : route.continue();
  });
  await page.goto("/map");
  await expect(page.locator("path[data-segment-id]").first()).toBeAttached();
  expect(attempts).toBe(2);
});
