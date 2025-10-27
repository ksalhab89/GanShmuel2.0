import { test, expect } from '@playwright/test'

/**
 * Provider Marketplace - Admin Approval Flow Tests
 */
test.describe('Admin Approval Panel', () => {
  let testCandidateEmail: string

  test.beforeEach(async ({ page }) => {
    await page.goto('/providers')

    // Create a test candidate for admin review
    testCandidateEmail = `admin.test.${Date.now()}@provider.com`

    await page.getByLabel('Company Name').fill('Admin Test Provider')
    await page.getByLabel('Contact Email').fill(testCandidateEmail)
    await page.getByLabel('Phone Number').fill('555-0123')
    await page.getByLabel('Location').fill('Jerusalem')
    await page.getByLabel('Products').click()
    await page.getByRole('option', { name: 'Grapes' }).click()
    await page.keyboard.press('Escape')
    await page.getByLabel('Number of Trucks').fill('8')
    await page.getByLabel('Capacity (tons/day)').fill('150')

    await page.getByRole('button', { name: 'Submit Registration' }).click()
    await expect(page.getByText(/Registration submitted successfully/i)).toBeVisible({
      timeout: 10000,
    })

    // Switch to Admin Review tab
    await page.getByRole('tab', { name: 'Admin Review' }).click()
  })

  test('should display candidate list', async ({ page }) => {
    // Wait for list to load
    await expect(page.getByRole('heading', { name: 'Candidate Applications' })).toBeVisible()

    // Table should be visible
    await expect(page.getByRole('table')).toBeVisible()

    // Should have table headers
    await expect(page.getByRole('columnheader', { name: 'Company' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Email' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible()
  })

  test('should filter candidates by status', async ({ page }) => {
    await page.getByRole('tab', { name: 'Admin Review' }).click()

    // Open status filter
    await page.getByLabel('Filter by Status').click()
    await page.getByRole('option', { name: 'Pending' }).click()

    // Should show pending candidates
    await expect(page.getByText('Admin Test Provider')).toBeVisible()

    // Change to approved filter
    await page.getByLabel('Filter by Status').click()
    await page.getByRole('option', { name: 'Approved' }).click()

    // Our test candidate shouldn't appear (it's pending)
    await expect(page.getByText('Admin Test Provider')).not.toBeVisible()
  })

  test('should display candidate details when clicked', async ({ page }) => {
    await page.getByRole('tab', { name: 'Admin Review' }).click()

    // Click on our test candidate
    await page.getByText('Admin Test Provider').click()

    // Detail panel should appear
    await expect(page.getByRole('heading', { name: 'Candidate Details' })).toBeVisible()

    // Verify details are shown
    await expect(page.getByText(testCandidateEmail)).toBeVisible()
    await expect(page.getByText('Jerusalem')).toBeVisible()
    await expect(page.getByText('8')).toBeVisible() // trucks
    await expect(page.getByText('150 tons/day')).toBeVisible()

    // Action buttons should be visible for pending candidates
    await expect(page.getByRole('button', { name: 'Approve' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible()
  })

  test('should successfully approve a candidate', async ({ page }) => {
    await page.getByRole('tab', { name: 'Admin Review' }).click()

    // Click on test candidate
    await page.getByText('Admin Test Provider').click()

    // Click approve button
    await page.getByRole('button', { name: 'Approve' }).click()

    // Confirmation dialog should appear
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText(/Are you sure you want to approve/i)).toBeVisible()

    // Confirm approval
    await page.getByRole('button', { name: 'Confirm' }).click()

    // Success message should appear
    await expect(page.getByText(/approved successfully/i)).toBeVisible({
      timeout: 10000,
    })
  })

  test('should successfully reject a candidate with reason', async ({ page }) => {
    await page.getByRole('tab', { name: 'Admin Review' }).click()

    // Click on test candidate
    await page.getByText('Admin Test Provider').click()

    // Click reject button
    await page.getByRole('button', { name: 'Reject' }).click()

    // Rejection dialog should appear
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByLabel('Rejection Reason')).toBeVisible()

    // Try to reject without reason - button should be disabled
    await expect(page.getByRole('button', { name: 'Reject' })).toBeDisabled()

    // Enter rejection reason
    await page.getByLabel('Rejection Reason').fill('Insufficient capacity for our requirements')

    // Now button should be enabled
    await expect(page.getByRole('button', { name: 'Reject' })).toBeEnabled()

    // Confirm rejection
    await page.getByRole('button', { name: 'Reject' }).click()

    // Success message should appear
    await expect(page.getByText(/rejected/i)).toBeVisible({
      timeout: 10000,
    })
  })

  test('should not show action buttons for already reviewed candidates', async ({ page }) => {
    await page.getByRole('tab', { name: 'Admin Review' }).click()

    // Click on test candidate and approve
    await page.getByText('Admin Test Provider').click()
    await page.getByRole('button', { name: 'Approve' }).click()
    await page.getByRole('button', { name: 'Confirm' }).click()

    // Wait for success
    await expect(page.getByText(/approved successfully/i)).toBeVisible({
      timeout: 10000,
    })

    // Reload the page
    await page.reload()
    await page.getByRole('tab', { name: 'Admin Review' }).click()

    // Click on the same candidate
    await page.getByText('Admin Test Provider').click()

    // Action buttons should not be visible (candidate is approved)
    await expect(page.getByRole('button', { name: 'Approve' })).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Reject' })).not.toBeVisible()
  })
})
