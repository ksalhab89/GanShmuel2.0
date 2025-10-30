import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Paper,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { providerApi } from '@/api/providerApi'
import axios from 'axios'
import type {
  CandidateStatus,
  ProductType,
  CandidateListParams,
} from '@/types/provider'

const getErrorMessage = (error: Error): string => {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message
  }
  return 'Unknown error'
}

const STATUS_COLORS: Record<
  CandidateStatus,
  'default' | 'success' | 'error'
> = {
  pending: 'default',
  approved: 'success',
  rejected: 'error',
}

const PRODUCTS: ProductType[] = ['apples', 'oranges', 'grapes', 'cherries']

interface Props {
  onSelectCandidate?: (id: string) => void
}

export default function CandidateList({ onSelectCandidate }: Props) {
  const [filters, setFilters] = useState<CandidateListParams>({
    page: 1,
    page_size: 10,
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['candidates', filters],
    queryFn: () => providerApi.listCandidates(filters),
  })

  const handleFilterChange = (field: keyof CandidateListParams, value: string | number | undefined) => {
    setFilters((prev) => ({ ...prev, [field]: value, page: 1 }))
  }

  if (error) {
    return (
      <Alert severity="error">
        Failed to load candidates: {getErrorMessage(error)}
      </Alert>
    )
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          Candidate Applications
        </Typography>

        {/* Filters */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Filter by Status</InputLabel>
              <Select
                value={filters.status || ''}
                label="Filter by Status"
                onChange={(e) =>
                  handleFilterChange(
                    'status',
                    e.target.value || undefined
                  )
                }
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="approved">Approved</MenuItem>
                <MenuItem value="rejected">Rejected</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Filter by Product</InputLabel>
              <Select
                value={filters.product || ''}
                label="Filter by Product"
                onChange={(e) =>
                  handleFilterChange(
                    'product',
                    e.target.value || undefined
                  )
                }
              >
                <MenuItem value="">All</MenuItem>
                {PRODUCTS.map((product) => (
                  <MenuItem key={product} value={product}>
                    {product.charAt(0).toUpperCase() + product.slice(1)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        {/* Table */}
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : !data || data.candidates.length === 0 ? (
          <Alert severity="info">No candidates found</Alert>
        ) : (
          <>
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Company</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>Phone</TableCell>
                    <TableCell>Products</TableCell>
                    <TableCell>Trucks</TableCell>
                    <TableCell>Capacity</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.candidates.map((candidate) => (
                    <TableRow
                      key={candidate.candidate_id}
                      hover
                      onClick={() => onSelectCandidate?.(candidate.candidate_id)}
                      sx={{ cursor: onSelectCandidate ? 'pointer' : 'default' }}
                    >
                      <TableCell>{candidate.company_name}</TableCell>
                      <TableCell>{candidate.contact_email}</TableCell>
                      <TableCell>{candidate.phone || 'N/A'}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {candidate.products.map((product) => (
                            <Chip
                              key={product}
                              label={product}
                              size="small"
                              variant="outlined"
                            />
                          ))}
                        </Box>
                      </TableCell>
                      <TableCell>{candidate.truck_count}</TableCell>
                      <TableCell>
                        {candidate.capacity_tons_per_day} tons/day
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={candidate.status}
                          color={STATUS_COLORS[candidate.status]}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {new Date(candidate.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Showing {data.candidates.length} of {data.pagination.total} candidates
            </Typography>
          </>
        )}
      </CardContent>
    </Card>
  )
}
