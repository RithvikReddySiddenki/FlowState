import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

// No route mocking or authentication bypass in the application. This cookie is
// seeded by smoke_stack.py exclusively in the isolated synthetic Compose DB.
test("manage applications through the real container API", async ({ page }, info) => {
  const { cookie } = JSON.parse(readFileSync(process.env.FLOWSTATE_LIVE_SESSION_FILE || "../../.tools/validation-session.json", "utf8"));
  await page.context().addCookies([{ name: "session", value: cookie, domain: "localhost", path: "/", httpOnly: true, sameSite: "Lax" }]);
  await page.goto("/dashboard");
  await expect(page.getByText("container-demo@example.test")).toBeVisible();
  const company = `Synthetic Browser ${info.project.name}`;
  await page.getByLabel("Company", { exact: true }).fill(company);
  await page.getByLabel("Role", { exact: true }).fill("Integration Engineer");
  await page.getByRole("button", { name: "Add application", exact: true }).click();
  const card = page.getByRole("article").filter({ hasText: company });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Recruiting stage").selectOption("Interview Scheduled");
  await page.getByLabel("Action required", { exact: true }).check();
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(card.getByText("Interview Scheduled", { exact: true })).toBeVisible();
  await card.getByRole("button", { name: "View history" }).click();
  const history = page.getByRole("region", { name: "Status history" });
  await expect(history.getByText("Application Received", { exact: true })).toBeVisible();
  await expect(history.getByText("Interview Scheduled", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: info.outputPath("real-stack-synthetic-data.png"), fullPage: true });
  page.once("dialog", dialog => dialog.accept());
  await card.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(card).toHaveCount(0);
  await page.getByRole("link", { name: "Account settings" }).click();
  await expect(page.getByRole("heading", { name: "Account settings" })).toBeVisible();
  await expect(page.getByText("Synthetic demo · container-demo@example.test")).toBeVisible();
});
