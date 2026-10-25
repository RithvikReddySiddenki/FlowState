import { test, expect } from "@playwright/test";

// Browser tests use synthetic API fixtures. These are frontend workflow tests,
// not a claim of real Google or full backend integration verification.
test.beforeEach(async ({ page }) => {
  let applications = [{ id: 1, company: "Example Labs", role: "Engineer", current_status: "Under Review", action_required: false, deadline: null, updated_at: "2026-10-24T12:00:00Z" }];
  let authenticated = true;
  await page.route("http://localhost:8000/**", async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let body: unknown = {};
    let status = 200;
    if (path === "/auth/me") { body = authenticated ? { user: { email: "demo@example.test" } } : { detail: "Sign in" }; status = authenticated ? 200 : 401; }
    else if (path === "/auth/logout") { authenticated = false; }
    else if (path === "/gmail/connection") body = { connected: false, last_synced_at: null, latest_run: null };
    else if (path === "/gmail/review/page") body = { items: [], total: 0, offset: 0, limit: 25 };
    else if (path.endsWith("/history")) body = [{ id: 1, current_status: "Under Review", source: "manual", created_at: "2026-10-24T12:00:00Z" }];
    else if (path.endsWith("/messages")) body = [];
    else if (path === "/applications" && request.method() === "GET") body = applications;
    else if (path === "/applications" && request.method() === "POST") {
      const item = { ...request.postDataJSON(), id: applications.length + 1, updated_at: new Date().toISOString() };
      applications.push(item); body = item; status = 201;
    } else if (/^\/applications\/\d+$/.test(path)) {
      const id = Number(path.split("/").pop());
      if (request.method() === "DELETE") { applications = applications.filter(a => a.id !== id); status = 204; }
      else { applications = applications.map(a => a.id === id ? { ...a, ...request.postDataJSON() } : a); body = applications.find(a => a.id === id); }
    } else { status = 404; body = { detail: "Unknown fixture route" }; }
    await route.fulfill({ status, contentType: "application/json", body: status === 204 ? "" : JSON.stringify(body) });
  });
});

test("create, edit, search, history, delete and logout", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByText("demo@example.test")).toBeVisible();
  await page.getByLabel("Company", { exact: true }).fill("Synthetic Studio");
  await page.getByLabel("Role", { exact: true }).fill("Designer");
  await page.getByRole("button", { name: "Add application", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Synthetic Studio", exact: true })).toBeVisible();
  const card = page.getByRole("article").filter({ hasText: "Synthetic Studio" });
  await card.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Role", { exact: true }).fill("Lead Designer");
  await page.getByLabel("Action required", { exact: true }).check();
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(card.getByText("Lead Designer")).toBeVisible();
  await page.getByLabel("Search", { exact: true }).fill("Synthetic");
  await expect(page.getByRole("article")).toHaveCount(1);
  await card.getByRole("button", { name: "View history" }).click();
  await expect(page.getByRole("region", { name: "Status history" })).toBeVisible();
  page.once("dialog", dialog => dialog.accept());
  await card.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByRole("article")).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("link", { name: "Sign in with Google" })).toBeVisible();
});

test("renders a responsive synthetic dashboard", async ({ page }, testInfo) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Application workspace" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Connect Gmail" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath("synthetic-dashboard.png"), fullPage: true });
});

test("unauthenticated users see sign in instead of private data", async ({ page }) => {
  await page.route("http://localhost:8000/auth/me", route => route.fulfill({ status: 401, json: { detail: "Sign in" } }));
  await page.goto("/dashboard");
  await expect(page.getByRole("link", { name: "Sign in with Google" })).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(0);
});

test("account settings offers connected-account controls", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Account settings" })).toBeVisible();
  await expect(page.getByText("Google account · demo@example.test")).toBeVisible();
  await expect(page.getByRole("link", { name: "Connect Gmail" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Delete account" })).toBeVisible();
});

test("expired Gmail mutations return the workspace to sign in", async ({ page }) => {
  await page.route("http://localhost:8000/gmail/connection", route => route.fulfill({ json: { connected: true, last_synced_at: null, latest_run: null } }));
  await page.route("http://localhost:8000/gmail/sync/start", route => route.fulfill({ status: 401, json: { detail: "Sign in to continue" } }));
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Sync / retry Gmail" }).click();
  await expect(page.getByRole("link", { name: "Sign in with Google" })).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(0);
});


test("review queue shows the full count and navigates beyond 200 messages", async ({ page }) => {
  await page.route("http://localhost:8000/gmail/review/page?**", route => {
    const url = new URL(route.request().url());
    const offset = Number(url.searchParams.get("offset") || 0);
    const items = Array.from({ length: Math.min(25, 205 - offset) }, (_, index) => ({
      id: offset + index + 1, subject: `Synthetic review ${offset + index + 1}`,
      sender: "ats@example.test", snippet: "Synthetic recruiting update", confidence: 0.55,
      explanation: "Application identity is incomplete", detected_status: "Under Review", review_required: true,
    }));
    return route.fulfill({ json: { items, total: 205, offset, limit: 25 } });
  });
  await page.goto("/dashboard");
  await page.getByText("205 messages need review", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Synthetic review 1", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Previous messages" })).toBeDisabled();
  for (let pageIndex = 1; pageIndex <= 8; pageIndex++) {
    await page.getByRole("button", { name: "Next messages" }).click();
    await expect(page.getByText(`Showing ${pageIndex * 25 + 1}-${Math.min((pageIndex + 1) * 25, 205)} of 205`, { exact: true })).toBeVisible();
  }
  await expect(page.getByRole("heading", { name: "Synthetic review 205", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Next messages" })).toBeDisabled();
  await page.getByRole("button", { name: "Previous messages" }).click();
  await expect(page.getByText("Showing 176-200 of 205", { exact: true })).toBeVisible();
});
