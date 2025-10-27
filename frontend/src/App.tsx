import { Routes, Route } from 'react-router-dom'
import { Container, AppBar, Toolbar, Typography, Box, Button } from '@mui/material'
import { Home } from '@mui/icons-material'
import { Link } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import ProviderMarketplace from './pages/ProviderMarketplace'

function App() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static" elevation={2}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Gan Shmuel Weight Management
          </Typography>
          <Button
            component={Link}
            to="/"
            color="inherit"
            startIcon={<Home />}
          >
            Home
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flex: 1 }}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/providers" element={<ProviderMarketplace />} />
          <Route path="/providers/*" element={<ProviderMarketplace />} />
        </Routes>
      </Container>

      <Box
        component="footer"
        sx={{
          py: 3,
          px: 2,
          mt: 'auto',
          backgroundColor: (theme) =>
            theme.palette.mode === 'light'
              ? theme.palette.grey[200]
              : theme.palette.grey[800],
        }}
      >
        <Container maxWidth="sm">
          <Typography variant="body2" color="text.secondary" align="center">
            © 2025 Gan Shmuel Industrial Weight Management System
          </Typography>
        </Container>
      </Box>
    </Box>
  )
}

export default App
