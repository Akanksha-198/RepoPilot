import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import { AuthProvider } from './auth.jsx';
import { ToastProvider } from './components/Toast.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  </ErrorBoundary>
);
