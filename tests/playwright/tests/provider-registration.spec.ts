import { test, expect } from '@playwright/test'

/**
 * Provider Marketplace - Registration Flow Tests
 */
test.describe('Provider Registration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/providers')
  })

  test('should display registration form', async ({ page }) => {
    // Verify we're on the registration tab by default
    await expect(page.getByRole('heading', { name: 'Register as Provider' })).toBeVisible()

    // Check all form fields are present
    await expect(page.getByLabel('Company Name')).toBeVisible()
    await expect(page.getByLabel('Contact Email')).toBeVisible()
    await expect(page.getByLabel('Phone Number')).toBeVisible()
    await expect(page.getByLabel('Location')).toBeVisible()
    await expect(page.getByLabel('Products')).toBeVisible()
    await expect(page.getByLabel('Number of Trucks')).toBeVisible()
    await expect(page.getByLabel('Capacity (tons/day)')).toBeVisible()
    await expect(page.getByLabel('Additional Notes')).toBeVisible()
  })

  test('should validate required fields', async ({ page }) => {
    // Try to submit empty form
    await page.getByRole('button', { name: 'Submit Registration' }).click()

    // HTML5 validation should prevent submission
    const companyInput = page.getByLabel('Company Name')
    await expect(companyInput).toHaveAttribute('required', '')
  })

  test('should successfully register a new candidate', async ({ page }) => {
    // Fill out the registration form
    await page.getByLabel('Company Name').fill('Test Provider Inc')
    await page.getByLabel('Contact Email').fill(`test.${Date.now()}@provider.com`)
    await page.getByLabel('Phone Number').fill('123-456-7890')
    await page.getByLabel('Location').fill('Tel Aviv')

    // Select products
    await page.getByLabel('Products').click()
    await page.getByRole('option', { name: 'Apples' }).click()
    await page.getByRole('option', { name: 'Oranges' }).click()
    // Click outside to close dropdown
    await page.keyboard.press('Escape')

    await page.getByLabel('Number of Trucks').fill('5')
    await page.getByLabel('Capacity (tons/day)').fill('100')
    await page.getByLabel('Additional Notes').fill('Premium quality fruits supplier')

    // Submit form
    await page.getByRole('button', { name: 'Submit Registration' }).click()

    // Wait for success message
    await expect(page.getByText(/Registration submitted successfully/i)).toBeVisible({
      timeout: 10000,
    })

    // Form should be cleared
    await expect(page.getByLabel('Company Name')).toHaveValue('')
  })

  test('should prevent duplicate email registration', async ({ page }) => {
    const duplicateEmail = 'duplicate@test.com'

    // First registration
    await page.getByLabel('Company Name').fill('First Company')
    await page.getByLabel('Contact Email').fill(duplicateEmail)
    await page.getByLabel('Phone Number').fill('111-111-1111')
    await page.getByLabel('Location').fill('Location 1')
    await page.getByLabel('Products').click()
    await page.getByRole('option', { name: 'Apples' }).click()
    await page.keyboard.press('Escape')
    await page.getByLabel('Number of Trucks').fill('3')
    await page.getByLabel('Capacity (tons/day)').fill('50')

    await page.getByRole('button', { name: 'Submit Registration' }).click()
    await expect(page.getByText(/Registration submitted successfully/i)).toBeVisible({
      timeout: 10000,
    })

    // Wait a moment for the form to reset
    await page.waitForTimeout(1000)

    // Try to register again with same email
    await page.getByLabel('Company Name').fill('Second Company')
    await page.getByLabel('Contact Email').fill(duplicateEmail)
    await page.getByLabel('Phone Number').fill('222-222-2222')
    await page.getByLabel('Location').fill('Location 2')
    await page.getByLabel('Products').click()
    await page.getByRole('option', { name: 'Oranges' }).click()
    await page.keyboard.press('Escape')
    await page.getByLabel('Number of Trucks').fill('4')
    await page.getByLabel('Capacity (tons/day)').fill('75')

    await page.getByRole('button', { name: 'Submit Registration' }).click()

    // Should show error for duplicate email
    await expect(page.getByText(/already exists|duplicate/i)).toBeVisible({
      timeout: 10000,
    })
  })

  test('should display form validation for email format', async ({ page }) => {
    await page.getByLabel('Company Name').fill('Test Company')
    await page.getByLabel('Contact Email').fill('invalid-email')
    await page.getByLabel('Phone Number').click()

    // HTML5 email validation should show error
    const emailInput = page.getByLabel('Contact Email')
    await expect(emailInput).toHaveAttribute('type', 'email')
  })
})
