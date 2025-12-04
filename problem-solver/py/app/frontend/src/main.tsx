import React from 'react'
import { createRoot } from 'react-dom/client'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LandingPage from './pages/LandingPage'
import App from './App'
import AuthApp from './AuthApp'
import './index.css'

function Root() {
  const { isAuthenticated } = useAuth();

  const url = new URL(window.location.href);
  const code = url.searchParams.get('code');

  if (code) {
    return <AuthApp />;
  }

  return isAuthenticated ? <App /> : <LandingPage />;
}

createRoot(document.getElementById('root')!).render(
  <AuthProvider>
    <Root />
  </AuthProvider>
)