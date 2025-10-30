import { describe, it, expect, beforeEach, vi } from 'vitest';
import axios from 'axios';
import { getCandidates, approveCandidate, rejectCandidate } from './providerApi';

// Mock axios
vi.mock('axios');
const mockedAxios = axios as any;

describe('Provider API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getCandidates', () => {
    it('fetches candidates successfully', async () => {
      const mockCandidates = [
        { id: 1, name: 'Provider 1', email: 'provider1@example.com', status: 'pending' },
        { id: 2, name: 'Provider 2', email: 'provider2@example.com', status: 'pending' },
      ];

      mockedAxios.get.mockResolvedValue({ data: mockCandidates });

      const result = await getCandidates();

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/provider/candidates');
      expect(result).toEqual(mockCandidates);
    });

    it('throws error when API call fails', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network error'));

      await expect(getCandidates()).rejects.toThrow('Network error');
    });
  });

  describe('approveCandidate', () => {
    it('approves candidate successfully', async () => {
      const mockResponse = { id: 1, status: 'approved' };
      mockedAxios.post.mockResolvedValue({ data: mockResponse });

      const result = await approveCandidate(1);

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/provider/candidates/1/approve');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('rejectCandidate', () => {
    it('rejects candidate with reason', async () => {
      const mockResponse = { id: 1, status: 'rejected' };
      mockedAxios.post.mockResolvedValue({ data: mockResponse });

      const result = await rejectCandidate(1, 'Invalid information');

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/provider/candidates/1/reject', {
        reason: 'Invalid information',
      });
      expect(result).toEqual(mockResponse);
    });
  });
});
