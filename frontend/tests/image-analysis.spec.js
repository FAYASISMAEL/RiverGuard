import { test, expect } from "@playwright/test";
import fs from "node:fs";
const metadata = JSON.parse(fs.readFileSync("../data/metadata.json", "utf8"));
const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9foAAAAASUVORK5CYII=",
  "base64",
);
const photos = Array.from({ length: 3 }, (_, i) => ({
  name: `photo-${i}.png`,
  mimeType: "image/png",
  buffer: png,
}));
const start = (page) =>
  page.goto(
    `/report?lat=${metadata.demo_location.latitude}&lon=${metadata.demo_location.longitude}`,
  );
async function infer(page, results, delay = 0) {
  let calls = 0;
  await page.route("**/api/ai/classify-contamination", async (route) => {
    const value = results[Math.min(calls++, results.length - 1)];
    if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
    await route.fulfill({ json: { success: true, image_results: [value] } });
  });
  return () => calls;
}
async function finish(page) {
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page
    .getByLabel("Description")
    .fill(
      "SAMPLE AI assisted visual observation, not a confirmed pollution finding.",
    );
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  const result = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/reports") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Submit observation", exact: true })
    .click();
  return (await result).json();
}
for (const correct of [false, true]) {
  test(`all photos retained, majority suggestion ${correct ? "corrected" : "confirmed"} and stored`, async ({
    page,
  }) => {
    const calls = await infer(page, [
      { category: "Plastic / Solid Waste", confidence: 0.94 },
      { category: "Plastic / Solid Waste", confidence: 0.86 },
      { category: "Water Discoloration", confidence: 0.55 },
    ]);
    let uploads = 0;
    page.on("request", (r) => {
      if (r.url().endsWith("/api/uploads")) uploads++;
    });
    await start(page);
    await page.getByLabel("Evidence photos").setInputFiles(photos);
    await expect(page.getByLabel("Contamination type")).toHaveValue(
      "Plastic / Solid Waste",
    );
    expect(calls()).toBe(3);
    await expect(page.locator(".ai-suggestion")).toContainText("90%");
    if (correct)
      await page
        .getByLabel("Contamination type")
        .selectOption("Industrial Discharge");
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.getByRole("button", { name: "Back", exact: true }).click();
    await expect(page.locator(".evidence-grid img")).toHaveCount(3);
    const report = await finish(page);
    expect(report.ai_detected_category).toBe("Plastic / Solid Waste");
    expect(report.category_source).toBe(
      correct ? "USER_CORRECTED" : "AI_CONFIRMED",
    );
    expect(report.image_urls).toHaveLength(3);
    expect(report.status).toBe("UNVERIFIED");
    expect(uploads).toBe(3);
    await page.goto("/admin");
    await page.getByLabel("Username", { exact: true }).fill("admin123");
    await page.getByLabel("Password", { exact: true }).fill("admin@123");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/admin\/dashboard$/);
    await page.goto("/admin/reports/" + report.id);
    await expect(page.locator(".ai-review")).toContainText(
      "Plastic / Solid Waste",
    );
    await expect(page.locator(".ai-review")).toContainText(
      correct ? "Citizen corrected" : "confirmed by citizen",
    );
  });
}

test("unclear image, manual choice, removal and delayed response cannot override choice", async ({
  page,
}) => {
  await infer(page, [{ category: "Dead Fish", confidence: 0.4 }], 800);
  await start(page);
  await page.getByLabel("Evidence photos").setInputFiles(photos[0]);
  await expect(page.locator(".ai-suggestion")).toContainText(
    "confidently identify",
  );
  await expect(page.getByLabel("Contamination type")).toHaveValue(
    "Other / Unclear",
  );
  await page.getByLabel("Contamination type").selectOption("Foam");
  await page.getByLabel("Evidence photos").setInputFiles(photos[1]);
  await expect(
    page.getByText("Analysing evidence", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Remove image 2", exact: true })
    .click();
  await expect(page.getByLabel("Contamination type")).toHaveValue("Foam");
  const report = await finish(page);
  expect(report.final_category).toBe("Foam");
  expect(report.category_source).toBe("USER_CORRECTED");
  expect(report.image_urls).toHaveLength(1);
});

test("AI outage remains submittable without uploading photos again", async ({
  page,
}) => {
  await page.route("**/api/ai/classify-contamination", (route) =>
    route.fulfill({ status: 503, json: { detail: "unavailable" } }),
  );
  await start(page);
  await page.getByLabel("Evidence photos").setInputFiles(photos[0]);
  await expect(page.locator(".ai-suggestion")).toContainText(
    "temporarily unavailable",
  );
  await page.getByLabel("Contamination type").selectOption("Dead Fish");
  const report = await finish(page);
  expect(report.category_source).toBe("MANUAL");
  expect(report.ai_confidence).toBeNull();
  expect(report.image_urls).toHaveLength(1);
});

test("retry analysis reuses the selected evidence without another upload", async ({
  page,
}) => {
  let analyses = 0,
    uploads = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/uploads")) uploads++;
  });
  await page.route("**/api/ai/classify-contamination", (route) => {
    analyses++;
    return route.fulfill({
      json:
        analyses === 1
          ? { success: false }
          : {
              success: true,
              image_results: [{ category: "Foam", confidence: 0.91 }],
            },
    });
  });
  await start(page);
  await page.getByLabel("Evidence photos").setInputFiles(photos[0]);
  await page
    .getByRole("button", { name: "Retry analysis", exact: true })
    .click();
  await expect(page.getByLabel("Contamination type")).toHaveValue("Foam");
  await expect(
    page.getByRole("button", { name: "Continue", exact: true }),
  ).toBeEnabled();
  expect(analyses).toBe(2);
  expect(uploads).toBe(1);
});
