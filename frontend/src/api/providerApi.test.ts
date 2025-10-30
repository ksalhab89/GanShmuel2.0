import { describe, it, expect, beforeEach, vi } from 'vitest'
import axios from 'axios'
import type { Candidate, CandidateCreate } from '@/types/provider'

// Mock axios with proper Vitest mocking
vi.mock('axios')

// Create mock axios instance
const mockAxiosInstance = {
  post: vi.fn(),
  get: vi.fn(),
}

// Set up axios.create to return our mock instance
vi.mocked(axios.create).mockReturnValue(mockAxiosInstance as any)

// Import providerApi AFTER mocking axios
const { providerApi } = await import('./providerApi')

describe('Provider API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockCandidate: Candidate = {
    id: '1',
    name: 'John Doe',
    email: 'john@example.com',
    phone: '+1234567890',
    status: 'pending',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
    version: 1
  }

  const mockCandidateCreate: CandidateCreate = {
    name: 'John Doe',
    email: 'john@example.com',
    phone: '+1234567890'
  }

  describe('registerCandidate', () => {
    it('registers a new candidate successfully', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: mockCandidate })

      const result = await providerApi.registerCandidate(mockCandidateCreate)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/candidates', mockCandidateCreate)
      expect(result).toEqual(mockCandidate)
    })

    it('throws error when registration fails', async () => {
      mockAxiosInstance.post.mockRejectedValue(new Error('Registration failed'))

      await expect(providerApi.registerCandidate(mockCandidateCreate)).rejects.toThrow('Registration failed')
    })
  })

  describe('listCandidates', () => {
    it('fetches candidates successfully', async () => {
      const mockResponse = {
        items: [mockCandidate],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1
      }

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse })

      const result = await providerApi.listCandidates()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/candidates', { params: undefined })
      expect(result).toEqual(mockResponse)
    })

    it('fetches candidates with filters', async () => {
      const mockResponse = {
        items: [mockCandidate],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1
      }

      const params = { status: 'pending', page: 1, page_size: 10 }
      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse })

      const result = await providerApi.listCandidates(params)

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/candidates', { params })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getCandidate', () => {
    it('fetches a single candidate successfully', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: mockCandidate })

      const result = await providerApi.getCandidate('1')

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/candidates/1')
      expect(result).toEqual(mockCandidate)
    })
  })

  describe('approveCandidate', () => {
    it('approves candidate successfully', async () => {
      const mockResponse = { message: 'Candidate approved', provider_id: 1 }
      const approval = { approved: true }

      mockAxiosInstance.post.mockResolvedValue({ data: mockResponse })

      const result = await providerApi.approveCandidate('1', approval)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/candidates/1/approve', approval)
      expect(result).toEqual(mockResponse)
    })

    it('rejects candidate with reason', async () => {
      const approval = { approved: false, reason: 'Invalid information' }

      mockAxiosInstance.post.mockRejectedValue(new Error('Rejection failed'))

      await expect(providerApi.approveCandidate('1', approval)).rejects.toThrow('Rejection failed')
    })
  })
})
