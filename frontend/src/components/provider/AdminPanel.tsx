import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Stack,
} from '@mui/material'
import { Check, Close } from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { providerApi } from '@/api/providerApi'
import axios from 'axios'

interface Props {
  candidateId: string | null
  onClose: () => void
}

const getErrorMessage = (error: Error): string => {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message
  }
  return 'Failed to process candidate'
}

export default function AdminPanel({ candidateId, onClose }: Props) {
  const queryClient = useQueryClient()
  const [rejectionReason, setRejectionReason] = useState('')
  const [showApproveDialog, setShowApproveDialog] = useState(false)
  const [showRejectDialog, setShowRejectDialog] = useState(false)

  const { data: candidate, isLoading } = useQuery({
    queryKey: ['candidate', candidateId],
    queryFn: () => providerApi.getCandidate(candidateId!),
    enabled: !!candidateId,
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) =>
      providerApi.approveCandidate(id, { approved: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] })
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] })
      setShowApproveDialog(false)
      onClose()
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      providerApi.approveCandidate(id, {
        approved: false,
        rejection_reason: reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] })
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] })
      setShowRejectDialog(false)
      setRejectionReason('')
      onClose()
    },
  })

  const handleApprove = () => {
    if (candidateId) {
      approveMutation.mutate(candidateId)
    }
  }

  const handleReject = () => {
    if (candidateId && rejectionReason.trim()) {
      rejectMutation.mutate({ id: candidateId, reason: rejectionReason })
    }
  }

  if (!candidateId) {
    return (
      <Card>
        <CardContent>
          <Alert severity="info">
            Select a candidate from the list to review
          </Alert>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    )
  }

  if (!candidate) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error">Candidate not found</Alert>
        </CardContent>
      </Card>
    )
  }

  const isPending = candidate.status === 'pending'

  return (
    <>
      <Card>
        <CardContent>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mb: 3,
            }}
          >
            <Typography variant="h5">Candidate Details</Typography>
            <Chip
              label={candidate.status}
              color={
                candidate.status === 'approved'
                  ? 'success'
                  : candidate.status === 'rejected'
                  ? 'error'
                  : 'default'
              }
            />
          </Box>

          {approveMutation.isSuccess && (
            <Alert severity="success" sx={{ mb: 2 }}>
              Candidate approved successfully! Provider created in billing
              system.
            </Alert>
          )}

          {rejectMutation.isSuccess && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Candidate rejected. Notification sent.
            </Alert>
          )}

          {(approveMutation.isError || rejectMutation.isError) && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {getErrorMessage(approveMutation.error || rejectMutation.error)}
            </Alert>
          )}

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Company Name
              </Typography>
              <Typography variant="body1" gutterBottom>
                {candidate.company_name}
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Contact Email
              </Typography>
              <Typography variant="body1" gutterBottom>
                {candidate.contact_email}
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Phone
              </Typography>
              <Typography variant="body1" gutterBottom>
                {candidate.phone}
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Location
              </Typography>
              <Typography variant="body1" gutterBottom>
                {candidate.location}
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Number of Trucks
              </Typography>
              <Typography variant="body1" gutterBottom>
                {candidate.truck_count}
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Daily Capacity
              </Typography>
              <Typography variant="body1" gutterBottom>
                {candidate.capacity_tons_per_day} tons/day
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle2" color="text.secondary">
                Products
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                {candidate.products.map((product) => (
                  <Chip key={product} label={product} variant="outlined" />
                ))}
              </Box>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle2" color="text.secondary">
                Created
              </Typography>
              <Typography variant="body1" gutterBottom>
                {new Date(candidate.created_at).toLocaleString()}
              </Typography>
            </Grid>
          </Grid>

          {isPending && (
            <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
              <Button
                variant="contained"
                color="success"
                startIcon={<Check />}
                onClick={() => setShowApproveDialog(true)}
                disabled={
                  approveMutation.isPending || rejectMutation.isPending
                }
              >
                Approve
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<Close />}
                onClick={() => setShowRejectDialog(true)}
                disabled={
                  approveMutation.isPending || rejectMutation.isPending
                }
              >
                Reject
              </Button>
            </Stack>
          )}
        </CardContent>
      </Card>

      {/* Approve Confirmation Dialog */}
      <Dialog open={showApproveDialog} onClose={() => setShowApproveDialog(false)}>
        <DialogTitle>Approve Candidate</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to approve <strong>{candidate.company_name}</strong>?
            This will create a provider in the billing system.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowApproveDialog(false)}>Cancel</Button>
          <Button
            onClick={handleApprove}
            variant="contained"
            color="success"
            disabled={approveMutation.isPending}
          >
            {approveMutation.isPending ? 'Approving...' : 'Confirm'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={showRejectDialog} onClose={() => setShowRejectDialog(false)}>
        <DialogTitle>Reject Candidate</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            Please provide a reason for rejecting <strong>{candidate.company_name}</strong>:
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Rejection Reason"
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            sx={{ mt: 2 }}
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowRejectDialog(false)}>Cancel</Button>
          <Button
            onClick={handleReject}
            variant="contained"
            color="error"
            disabled={
              !rejectionReason.trim() || rejectMutation.isPending
            }
          >
            {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
