import { test, expect } from "@playwright/test";
test("citizen report, downstream analysis, photo, simulated alert and verification", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /A healthier river/ }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Report contamination", exact: true })
    .click();
  await page
    .getByLabel("Description")
    .fill(
      "Unusual dark water observed near the bank during the demonstration.",
    );
  await page.getByLabel("Observation photo").setInputFiles({
    name: "evidence.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9foAAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(
    page.locator(".leaflet-overlay-pane path").first(),
  ).toBeVisible();
  // Click the visible upstream river line, using the actual map UI.
  await page
    .locator('.leaflet-overlay-pane path[stroke="#3493a9"]')
    .first()
    .click();
  await expect(page.getByText(/Nearest river segment:/)).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Submit observation" }).click();
  await expect(
    page.getByText("Your observation has been submitted.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByAltText("Citizen-submitted observation evidence"),
  ).toBeVisible();
  const reportUrl = new URL(page.url()).pathname;
  await page.goto(reportUrl + "?authority=1");
  await page
    .getByRole("button", { name: "Mark under review", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Verify", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Resolve", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Send simulated alert" })
    .first()
    .click();
  await page.getByRole("button", { name: "Acknowledge alert" }).first().click();
  await expect(page.getByText("Acknowledged", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Resolve", exact: true }).click();
  await expect(
    page.getByText("This report has reached its final status."),
  ).toBeVisible();
  await page.goto("/insights");
  await expect(
    page.getByRole("heading", { name: "Repeated report locations" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("demo highlights route and mobile has no horizontal overflow", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Load Demo Scenario" }).click();
  await expect(
    page.getByRole("heading", { name: "Industrial Discharge" }),
  ).toBeVisible();
  await expect(
    page.locator(".asset").filter({ hasText: "Aluva water intake" }),
  ).toBeVisible();
  await expect(
    page.locator('.leaflet-overlay-pane path[stroke="#ed754b"]').first(),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/live-map.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/", "/map", "/report", "/insights", "/authority"]) {
    await page.goto(path);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await page.goto("/");
  await expect(
    page.locator(".leaflet-overlay-pane path").first(),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/mobile-home.png",
    fullPage: true,
  });
});

test("empty states, backend failure and invalid image are understandable", async ({
  page,
}) => {
  await page.route("**/api/reports", (route) => route.fulfill({ json: [] }));
  await page.goto("/map");
  await expect(
    page.getByText(
      "No observations match. Submit a report or load the demo from Overview.",
    ),
  ).toBeVisible();
  await page.unroute("**/api/reports");
  await page.route("**/api/reports", (route) => route.abort());
  await page.getByRole("button", { name: "Refresh reports" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Could not reach the server",
  );
  await page.goto("/report");
  await page
    .getByLabel("Observation photo")
    .setInputFiles({
      name: "invalid.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("not an image"),
    });
  await expect(page.getByRole("alert")).toContainText("Choose a JPEG");
});
