import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';

describe('App', () => {
  it('renders app bar with title', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    expect(screen.getByText('Gan Shmuel Weight Management')).toBeInTheDocument();
  });

  it('renders home button', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    expect(screen.getByRole('button', { name: /home/i })).toBeInTheDocument();
  });

  it('renders landing page by default', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Landing page should render health check section
    expect(screen.getByText(/Service Health Status/i)).toBeInTheDocument();
  });
});
