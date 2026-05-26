import { expect, test } from "@playwright/test";

const FILE_TYPES = ["pdf", "image", "docx", "xlsx", "pptx"] as const;

for (const fileType of FILE_TYPES) {
  test(`renders completed ${fileType} job`, async ({ page }) => {
    await mockCompletedJob(page, fileType);
    await page.goto("/jobs/job-123");

    await expect(page.getByRole("heading", { name: /1 difference/ })).toBeVisible();
    await expect(page.locator(".badge", { hasText: fileTypeLabel(fileType) }).first()).toBeVisible();
    await expect(page.getByText("Updated amount").first()).toBeVisible();
    await expect(page.getByText("Risk Summary")).toBeVisible();
  });
}

test("home page exposes upload and history workflow", async ({ page }) => {
  await page.route("**/v1/jobs?limit=20", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { items: [], total: 0 }
    });
  });
  await page.route("**/v1/metrics", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        job_status_counts: { queued: 0, running: 0, completed: 0, failed: 0, cancelled: 0 },
        queue_depth: 0,
        failure_rate: 0,
        alerts: []
      }
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Upload Documents" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent Jobs" })).toBeVisible();
});

async function mockCompletedJob(page: import("@playwright/test").Page, fileType: string) {
  await page.route("**/v1/jobs/job-123", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        job_id: "job-123",
        status: "completed",
        file_a: `a.${fileType}`,
        file_b: `b.${fileType}`,
        file_a_type: fileType,
        file_b_type: fileType,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    });
  });
  await page.route("**/v1/jobs/job-123/result?result_schema_version=2.1", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: resultPayload(fileType)
    });
  });
  await page.route("**/v1/jobs/job-123/artifact-link/a", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { url: "/mock/a", signed: false, label: "a" }
    });
  });
  await page.route("**/v1/jobs/job-123/artifact-link/b", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { url: "/mock/b", signed: false, label: "b" }
    });
  });
  await page.route("**/mock/**", async (route) => {
    await route.fulfill({
      body: Buffer.from("mock artifact"),
      contentType: fileType === "pdf" ? "application/pdf" : "image/png"
    });
  });
}

function resultPayload(fileType: string) {
  return {
    result_schema_version: "2.1",
    summary: "1 difference(s) detected",
    file_type: fileType,
    changes: [
      {
        id: "chg-001",
        type: "modified",
        category: fileType === "xlsx" ? "formula" : "text",
        severity: "high",
        confidence: 0.95,
        message: "Updated amount",
        source_ref: sourceRef(fileType),
        semantic_label: "meaning-changed",
        semantic_score: 0.92,
        bbox: { page: 1, x: 0.2, y: 0.2, width: 0.3, height: 0.1 }
      }
    ],
    semantic: {
      summary: ["Meaning changed in a high-value clause."],
      risk_summary: {
        high_risk_count: 1,
        findings: [{ change_id: "chg-001", domain: "finance", reason: "Amount changed" }]
      }
    },
    viewer_hints: {
      coordinate_policy: "normalized_0_to_1",
      artifact_labels: ["a", "b"],
      renderer: { type: fileType, supports_overlays: true, primary_axis: "page" },
      anchors: { pages: [1], slides: [1], sheets: ["Summary"], cells: ["B2"] },
      filters: {
        categories: ["text"],
        severities: ["high"],
        semantic_labels: ["meaning-changed"]
      },
      counts: { change_count: 1 }
    }
  };
}

function sourceRef(fileType: string) {
  if (fileType === "xlsx") {
    return { document: "both", sheet: "Summary", cell: "B2" };
  }
  if (fileType === "pptx") {
    return { document: "both", slide: 1 };
  }
  if (fileType === "docx") {
    return { document: "both", part: "body", paragraph: 1 };
  }
  return { document: "both", page: 1 };
}

function fileTypeLabel(fileType: string) {
  return fileType === "image" ? "Image" : fileType.toUpperCase();
}
