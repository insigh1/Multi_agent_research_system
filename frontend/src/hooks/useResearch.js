import { useState, useCallback } from 'react';
import { api } from '../utils/api';

export const useResearch = () => {
  const [isResearching, setIsResearching] = useState(false);
  const [progress, setProgress] = useState(null);
  const [results, setResults] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const [error, setError] = useState(null);
  const [metrics, setMetrics] = useState(null);

  const startResearch = useCallback(async (request, onWebSocketConnect) => {
    if (!request.query.trim()) return;
    
    // Store current query globally for architecture diagram
    window.currentQuery = request.query.trim();
    
    setIsResearching(true);
    setError(null);
    setResults(null);
    setProgress(null);
    
    try {
      const data = await api.startResearch(request);
      
      if (data.session_id) {
        setCurrentSession(data.session_id);
        onWebSocketConnect?.(data.session_id);
      } else {
        setError(data.message);
        setIsResearching(false);
      }
    } catch (err) {
      setError('Failed to start research: ' + err.message);
      setIsResearching(false);
    }
  }, []);

  const fetchResults = useCallback(async (sessionId) => {
    try {
      const data = await api.getResults(sessionId);
      setResults(data);
      
      // Also fetch metrics
      try {
        const metricsData = await api.getMetrics(sessionId);
        if (metricsData.success && metricsData.metrics && metricsData.metrics.message !== "No detailed metrics available for this session") {
          setMetrics(metricsData.metrics);
        }
      } catch (err) {
        console.warn('Failed to fetch metrics:', err.message);
      }
    } catch (err) {
      setError('Failed to fetch results: ' + err.message);
    }
  }, []);

  return {
    isResearching,
    setIsResearching,
    progress,
    setProgress,
    results,
    setResults,
    currentSession,
    setCurrentSession,
    error,
    setError,
    metrics,
    setMetrics,
    startResearch,
    fetchResults
  };
}; 