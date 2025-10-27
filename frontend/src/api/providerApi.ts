/**
 * API client for Provider Registration Service
 */
import axios, { AxiosInstance } from 'axios'
import type {
  Candidate,
  CandidateCreate,
  CandidateApproval,
  CandidateListParams,
  CandidateListResponse,
} from '@/types/provider'

class ProviderApi {
  private client: AxiosInstance

  constructor(baseURL: string = '/api/providers') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  /**
   * Register a new candidate
   */
  async registerCandidate(data: CandidateCreate): Promise<Candidate> {
    const response = await this.client.post<Candidate>('/candidates', data)
    return response.data
  }

  /**
   * Get list of candidates with optional filters
   */
  async listCandidates(
    params?: CandidateListParams
  ): Promise<CandidateListResponse> {
    const response = await this.client.get<CandidateListResponse>(
      '/candidates',
      { params }
    )
    return response.data
  }

  /**
   * Get a single candidate by ID
   */
  async getCandidate(id: string): Promise<Candidate> {
    const response = await this.client.get<Candidate>(`/candidates/${id}`)
    return response.data
  }

  /**
   * Approve or reject a candidate
   */
  async approveCandidate(
    id: string,
    approval: CandidateApproval
  ): Promise<{ message: string; provider_id?: number }> {
    const response = await this.client.post<{
      message: string
      provider_id?: number
    }>(`/candidates/${id}/approve`, approval)
    return response.data
  }
}

// Export singleton instance
export const providerApi = new ProviderApi()
