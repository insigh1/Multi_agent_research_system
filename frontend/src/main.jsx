import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import { ResearchProvider } from './context/ResearchContext.jsx';

// Create root and render the app
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ResearchProvider>
      <App />
    </ResearchProvider>
  </React.StrictMode>
); 