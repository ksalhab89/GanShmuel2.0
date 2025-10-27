import { useState } from 'react'
import { Box, Tabs, Tab, Grid } from '@mui/material'
import RegistrationForm from '@/components/provider/RegistrationForm'
import CandidateList from '@/components/provider/CandidateList'
import AdminPanel from '@/components/provider/AdminPanel'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`provider-tabpanel-${index}`}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  )
}

export default function ProviderMarketplace() {
  const [tabValue, setTabValue] = useState(0)
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(
    null
  )

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
    // Clear selection when switching tabs
    if (newValue !== 1) {
      setSelectedCandidateId(null)
    }
  }

  const handleSelectCandidate = (id: string) => {
    setSelectedCandidateId(id)
    // Scroll to admin panel
    const panel = document.getElementById('admin-panel')
    if (panel) {
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const handleCloseAdminPanel = () => {
    setSelectedCandidateId(null)
  }

  return (
    <Box>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Register" />
          <Tab label="Admin Review" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <RegistrationForm />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <CandidateList onSelectCandidate={handleSelectCandidate} />
          </Grid>

          {selectedCandidateId && (
            <Grid item xs={12} id="admin-panel">
              <AdminPanel
                candidateId={selectedCandidateId}
                onClose={handleCloseAdminPanel}
              />
            </Grid>
          )}
        </Grid>
      </TabPanel>
    </Box>
  )
}
