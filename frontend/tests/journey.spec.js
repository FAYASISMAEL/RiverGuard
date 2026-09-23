import { test, expect } from "@playwright/test";
import fs from "node:fs";
const metadata = JSON.parse(fs.readFileSync("../data/metadata.json", "utf8"));
const river = JSON.parse(
  fs.readFileSync("../data/river_network.geojson", "utf8"),
);
const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9foAAAAASUVORK5CYII=",
  "base64",
);
const photos = Array.from({ length: 3 }, (_, i) => ({
  name: `evidence-${i + 1}.png`,
  mimeType: "image/png",
  buffer: png,
}));
async function signIn(page) {
  await page.goto("/admin");
  await page.getByLabel("Username", { exact: true }).fill("admin123");
  await page.getByLabel("Password", { exact: true }).fill("admin@123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/dashboard$/);
}
async function clickRiver(page, id, fraction = 0.74) {
  const path = page.locator(`path[data-segment-id="${id}"]`);
  await expect(path).toBeAttached();
  const location = await path.evaluate((node, f) => {
    const p = node.getPointAtLength(node.getTotalLength() * f);
    const screen = new DOMPoint(p.x, p.y).matrixTransform(node.getScreenCTM());
    return { x: screen.x, y: screen.y };
  }, fraction);
  await page.mouse.click(location.x, location.y);
}

test("three photos: river click → citizen history → admin case → emergency response → resolved", async ({
  page,
  request,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/map");
  await expect(
    page.getByRole("link", { name: "Authority", exact: true }),
  ).toHaveCount(0);
  const analysis = await (
    await request.post("/api/analyze", { data: metadata.demo_location })
  ).json();
  await page.locator(".leaflet-control-layers").hover();
  await page.getByLabel("Citizen observations", { exact: true }).uncheck();
  await page.getByLabel("intakes", { exact: true }).uncheck();
  await page.getByLabel("settlements", { exact: true }).uncheck();
  await page.getByLabel("monitoring points", { exact: true }).uncheck();
  await clickRiver(page, analysis.snapped_location.segment_id);
  await expect(
    page.getByRole("heading", { name: "Report an Observation Here" }),
  ).toBeVisible();
  await expect(
    page.getByText("Location snapped to the nearest Periyar River segment.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByLabel("Contamination type").selectOption("Dead Fish");
  await page
    .getByRole("link", { name: "Report Observation →", exact: true })
    .click();
  await page
    .getByLabel("Description")
    .fill(
      "SAMPLE E2E: three evidence photos of a dead fish observation for demonstration.",
    );
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Evidence photos").setInputFiles(photos);
  await expect(page.locator(".evidence-grid img")).toHaveCount(3);
  await page
    .getByRole("button", { name: "Remove image 2", exact: true })
    .click();
  await expect(page.locator(".evidence-grid img")).toHaveCount(2);
  await page.getByLabel("Evidence photos").setInputFiles(photos[1]);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByText(/Nearest River Segment:/)).toBeVisible();
  await page.screenshot({
    path: "test-results/river-selection.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page
    .getByRole("button", { name: "Submit observation", exact: true })
    .click();
  await expect(
    page.getByText("Your observation has been submitted.", { exact: false }),
  ).toBeVisible();
  const reportPath = new URL(page.url()).pathname,
    id = reportPath.split("/").at(-1);
  await expect(page.locator(".evidence-grid img")).toHaveCount(3);
  await page
    .getByRole("button", { name: "View evidence image 1", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Close image viewer" }).click();
  await page.reload();
  await expect(page.locator(".evidence-grid img")).toHaveCount(3);
  await page.goto("/history");
  await page.getByLabel("Search history").fill(id);
  await expect(page.locator(".history-card")).toHaveCount(1);
  await signIn(page);
  await page.goto("/admin/reports/" + id);
  await expect(page.locator(".evidence-grid img")).toHaveCount(3);
  await page
    .getByRole("button", { name: "Accept / Start Review", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: /CASE-/ })).toBeVisible();
  const caseId = await page
    .getByRole("heading", { name: /CASE-/ })
    .textContent();
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Emergency action panel" }),
  ).toBeVisible();
  for (const name of [
    "Generate Authority Alert",
    "Notify Water Intake",
    "Request Field Inspection",
    "Notify Monitoring Point",
    "Generate Community Advisory",
    "Mark Under Control",
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(
      page.getByText(name + " — Simulated", { exact: true }),
    ).toBeVisible();
  }
  await page.screenshot({
    path: "test-results/admin-case.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Acknowledge alert" }).first().click();
  await page.getByRole("button", { name: "Resolve Case", exact: true }).click();
  await expect(
    page.getByText("This report has reached its final status."),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: caseId })).toBeVisible();
  await page.goto("/admin/reports");
  await page.getByLabel("Search reports").fill(caseId);
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await page.goto("/history");
  await page.getByLabel("Search history").fill(id);
  await expect(page.locator(".history-card")).toContainText("RESOLVED");
  expect(errors).toEqual([]);
});

test("login validation, protected routes, rejection, filters and logout", async ({
  page,
  request,
}) => {
  for (const url of ["/admin/dashboard", "/admin/reports", "/admin/cases"]) {
    await page.goto(url);
    await expect(page).toHaveURL(/\/admin$/);
  }
  await page.getByLabel("Username", { exact: true }).fill("Admin123");
  await page.getByLabel("Password", { exact: true }).fill("wrong");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Invalid username or password.",
  );
  const report = await (await request.post("/api/demo")).json();
  await page.goto("/reports/" + report.id + "?authority=1");
  await expect(
    page.getByRole("button", { name: "Verify", exact: true }),
  ).toHaveCount(0);
  await signIn(page);
  await page.reload();
  await expect(page).toHaveURL(/\/admin\/dashboard$/);
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await page.screenshot({
    path: "test-results/admin-dashboard.png",
    fullPage: true,
  });
  await page.goto("/admin/reports/" + report.id);
  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(
    page.getByText("This report has reached its final status."),
  ).toBeVisible();
  await page.goto("/admin/reports");
  await page.getByLabel("Search reports").fill(report.id);
  await page.getByLabel("Report status filter").selectOption("REJECTED");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByLabel("Report status filter").selectOption("VERIFIED");
  await expect(page.getByText("No matching reports.")).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/admin/cases");
  await expect(page).toHaveURL(/\/admin$/);
});

test("responsive pages, demo route, error states and evidence validation", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Protect the river/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/home-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Load Demo Scenario" }).click();
  await expect(page.locator('path[stroke="#ed754b"]').first()).toBeAttached();
  await page.screenshot({ path: "test-results/live-map.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of [
    "/",
    "/map",
    "/report",
    "/history",
    "/hotspots",
    "/about",
    "/admin",
  ]) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page.goto("/");
  await page.screenshot({
    path: "test-results/mobile-home.png",
    fullPage: true,
  });
  await page.route("**/api/reports", (route) => route.fulfill({ json: [] }));
  await page.goto("/history");
  await expect(page.getByText("No matching observations yet.")).toBeVisible();
  await page.unroute("**/api/reports");
  await page.route("**/api/reports", (route) => route.abort());
  await page.getByRole("button", { name: "Refresh history" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Could not reach the server",
  );
  await page.goto("/report");
  await page
    .getByLabel("Description")
    .fill("Test invalid evidence selection in the browser.");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Evidence photos").setInputFiles({
    name: "bad.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("bad"),
  });
  await expect(page.getByRole("alert")).toContainText("Choose JPEG");
  await page
    .getByLabel("Evidence photos")
    .setInputFiles([...photos, ...photos]);
  await expect(page.getByRole("alert")).toContainText("no more than 5");
});

test("visual alignment at upstream, middle, tributary, confluence, coastal and nearby points", async ({
  page,
}) => {
  const main = river.features.filter((f) => f.properties.mainstem);
  const upstream = [...main].sort(
    (a, b) =>
      Math.min(...a.geometry.coordinates.map((c) => c[1])) -
      Math.min(...b.geometry.coordinates.map((c) => c[1])),
  )[0];
  const middle = main.find((f) =>
    f.geometry.coordinates.some((c) => c[0] > 76.9 && c[0] < 77 && c[1] > 9.9),
  );
  const tributary = river.features.find(
    (f) => f.properties.name === "Muthirapuzha",
  );
  const coast = [...main].sort(
    (a, b) =>
      Math.min(...a.geometry.coordinates.map((c) => c[0])) -
      Math.min(...b.geometry.coordinates.map((c) => c[0])),
  )[0];
  const node = tributary.properties.downstream_node,
    confluence = river.features.find(
      (f) => f.properties.upstream_node === node,
    );
  const fixtures = [
    ["upstream", upstream],
    ["middle", middle],
    ["tributary", tributary],
    ["confluence", confluence],
    ["coastal", coast],
  ].map(([name, f]) => ({
    name,
    coord:
      f.geometry.coordinates[
        name === "confluence"
          ? 0
          : Math.floor(f.geometry.coordinates.length / 2)
      ],
  }));
  fixtures.push({
    name: "near-river",
    coord: [
      metadata.demo_location.longitude,
      metadata.demo_location.latitude + 0.0002,
    ],
  });
  for (const {
    name,
    coord: [lon, lat],
  } of fixtures) {
    await page.goto(`/report?lat=${lat}&lon=${lon}`);
    await page
      .getByLabel("Description")
      .fill("SAMPLE alignment check at " + name + " river location.");
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await expect(page.getByText(/Nearest River Segment:/)).toBeVisible();
    await expect(page.locator("path[data-segment-id]").first()).toBeAttached();
    await expect(page.locator('path[stroke="#ed754b"]').first()).toBeAttached();
    await expect
      .poll(
        () =>
          page
            .locator(".leaflet-tile")
            .evaluateAll(
              (nodes) =>
                nodes.length > 0 &&
                nodes.every((n) => n.complete && n.naturalWidth > 0),
            ),
        { timeout: 20000 },
      )
      .toBe(true);
    await page.screenshot({
      path: `test-results/alignment-${name}.png`,
      fullPage: true,
    });
    if (name === "near-river") {
      await page
        .getByRole("button", { name: "Zoom out", exact: true })
        .click({ clickCount: 3 });
      const map = page.locator(".leaflet-container");
      await map.click({ position: { x: 70, y: 95 } });
      await expect(page.getByRole("alert")).toContainText(
        "too far from the mapped river",
      );
    }
  }
});
