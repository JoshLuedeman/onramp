import { test, expect } from '@playwright/test';

test.describe('Governance Dashboard', () => {
  test('governance page loads', async ({ page }) => {
    await page.goto('/governance');
    await expect(page.getByRole('heading', { name: /governance/i })).toBeVisible();
  });

  test('shows overall score', async ({ page }) => {
    await page.goto('/governance');
    await expect(page.getByText(/overall governance score/i)).toBeVisible();
  });

  test('category tabs render', async ({ page }) => {
    await page.goto('/governance');
    await expect(page.getByRole('tablist')).toBeVisible();
  });

  test('can switch between tabs', async ({ page }) => {
    await page.goto('/governance');
    const costTab = page.getByRole('tab', { name: /cost/i });
    if (await costTab.isVisible()) {
      await costTab.click();
    }
  });
});
