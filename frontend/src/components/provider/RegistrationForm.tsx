import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  OutlinedInput,
  Alert,
  CircularProgress,
} from '@mui/material'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { providerApi } from '@/api/providerApi'
import axios from 'axios'
import type { CandidateCreate, ProductType } from '@/types/provider'

const PRODUCTS: ProductType[] = ['apples', 'oranges', 'grapes', 'cherries']

const getErrorMessage = (error: Error): string => {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message
  }
  return 'Failed to submit registration'
}

export default function RegistrationForm() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<CandidateCreate>({
    company_name: '',
    contact_email: '',
    phone: '',
    products: [],
    truck_count: 1,
    capacity_tons_per_day: 0,
    location: '',
    additional_notes: '',
  })

  const mutation = useMutation({
    mutationFn: (data: CandidateCreate) => providerApi.registerCandidate(data),
    onSuccess: () => {
      // Invalidate candidates list to refetch
      queryClient.invalidateQueries({ queryKey: ['candidates'] })
      // Reset form
      setFormData({
        company_name: '',
        contact_email: '',
        phone: '',
        products: [],
        truck_count: 1,
        capacity_tons_per_day: 0,
        location: '',
        additional_notes: '',
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate(formData)
  }

  const handleChange = (field: keyof CandidateCreate, value: string | ProductType[]) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          Register as Provider
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Fill out this form to apply as a new provider for Gan Shmuel
        </Typography>

        {mutation.isSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Registration submitted successfully! Your application is pending
            review.
          </Alert>
        )}

        {mutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {getErrorMessage(mutation.error)}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Company Name"
                required
                value={formData.company_name}
                onChange={(e) => handleChange('company_name', e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Contact Email"
                type="email"
                required
                value={formData.contact_email}
                onChange={(e) =>
                  handleChange('contact_email', e.target.value)
                }
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Phone Number"
                required
                value={formData.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Location"
                required
                value={formData.location}
                onChange={(e) => handleChange('location', e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth required>
                <InputLabel>Products</InputLabel>
                <Select
                  multiple
                  value={formData.products}
                  onChange={(e) =>
                    handleChange('products', e.target.value as ProductType[])
                  }
                  input={<OutlinedInput label="Products" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {PRODUCTS.map((product) => (
                    <MenuItem key={product} value={product}>
                      {product.charAt(0).toUpperCase() + product.slice(1)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Number of Trucks"
                type="number"
                required
                inputProps={{ min: 1 }}
                value={formData.truck_count}
                onChange={(e) =>
                  handleChange('truck_count', parseInt(e.target.value) || 1)
                }
              />
            </Grid>

            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Capacity (tons/day)"
                type="number"
                required
                inputProps={{ min: 0, step: 0.1 }}
                value={formData.capacity_tons_per_day}
                onChange={(e) =>
                  handleChange(
                    'capacity_tons_per_day',
                    parseFloat(e.target.value) || 0
                  )
                }
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Additional Notes"
                multiline
                rows={3}
                value={formData.additional_notes}
                onChange={(e) =>
                  handleChange('additional_notes', e.target.value)
                }
              />
            </Grid>

            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={mutation.isPending}
                startIcon={
                  mutation.isPending ? (
                    <CircularProgress size={20} />
                  ) : undefined
                }
              >
                {mutation.isPending ? 'Submitting...' : 'Submit Registration'}
              </Button>
            </Grid>
          </Grid>
        </Box>
      </CardContent>
    </Card>
  )
}
