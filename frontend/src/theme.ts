import { createTheme } from '@mui/material/styles'

// Create a theme instance for Gan Shmuel
const theme = createTheme({
  palette: {
    primary: {
      main: '#2e7d32', // Green for agriculture/factory theme
      light: '#60ad5e',
      dark: '#005005',
    },
    secondary: {
      main: '#ff6f00', // Orange for accents
      light: '#ffa040',
      dark: '#c43e00',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
  },
})

export default theme
