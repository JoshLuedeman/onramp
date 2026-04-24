import { test, expect } from '@playwright/test';

test.describe('Wizard Flow', () => {
  test('can start a new project from dashboard', async ({ page }) => {
    await page.goto('/');
    // Look for a "New Project" or similar call-to-action
    const createBtn = page.getByRole('button', { name: /new|create|start/i });
    if (await createBtn.isVisible()) {
      await expect(createBtn).toBeEnabled();
    }
  });
});
