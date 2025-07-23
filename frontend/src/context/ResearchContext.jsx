import React, { createContext, useContext, useReducer, useCallback, useRef } from 'react';
import { api, createWebSocketConnection } from '../utils/api';

// Initial state
const initialState = {
  // Research state
  status: 'idle', // 'idle' | 'researching' | 'completed' | 'failed'
  currentStage: null,
  
  // Data
  query: '',
  maxQuestions: 5,
  results: null,
  metrics: null,
  currentSession: null,
  
  // Progress tracking
  progress: null,
  progressPercentage: 0,
  currentOperation: null,
  
  // Real-time metrics
  tokensUsed: 0,
  estimatedCost: 0,
  apiCallsMade: 0,
  duration: null,
  
  // UI state
  showArchitecture: true,
  showApiConfig: false,
  showModelConfig: false,
  error: null,
  
  // WebSocket state
  isConnected: false
};

// Action types
const ActionTypes = {
  // Research lifecycle
  START_RESEARCH: 'START_RESEARCH',
  RESEARCH_COMPLETED: 'RESEARCH_COMPLETED',
  RESEARCH_FAILED: 'RESEARCH_FAILED',
  
  // Progress updates
  UPDATE_PROGRESS: 'UPDATE_PROGRESS',
  UPDATE_METRICS: 'UPDATE_METRICS',
  
  // Data updates
  SET_QUERY: 'SET_QUERY',
  SET_MAX_QUESTIONS: 'SET_MAX_QUESTIONS',
  SET_RESULTS: 'SET_RESULTS',
  SET_METRICS: 'SET_METRICS',
  SET_SESSION: 'SET_SESSION',
  
  // UI state
  TOGGLE_ARCHITECTURE: 'TOGGLE_ARCHITECTURE',
  TOGGLE_API_CONFIG: 'TOGGLE_API_CONFIG',
  TOGGLE_MODEL_CONFIG: 'TOGGLE_MODEL_CONFIG',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
  
  // WebSocket
  WEBSOCKET_CONNECTED: 'WEBSOCKET_CONNECTED',
  WEBSOCKET_DISCONNECTED: 'WEBSOCKET_DISCONNECTED',
  
  // Reset
  RESET_RESEARCH: 'RESET_RESEARCH'
};

// Reducer function
const researchReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.START_RESEARCH:
      return {
        ...state,
        status: 'researching',
        currentStage: null,
        error: null,
        results: null,
        progressPercentage: 0,
        tokensUsed: 0,
        estimatedCost: 0,
        apiCallsMade: 0
      };
    
    case ActionTypes.UPDATE_PROGRESS:
      const { progress } = action;
      const newState = { ...state, progress };
      
      // Update progress percentage
      if (progress.progress_percentage !== undefined) {
        newState.progressPercentage = progress.progress_percentage;
      }
      
      // Update current operation
      if (progress.current_operation) {
        newState.currentOperation = progress.current_operation;
      }
      
      // Update real-time metrics
      if (progress.tokens_used !== undefined) {
        newState.tokensUsed = progress.tokens_used;
      }
      if (progress.estimated_cost !== undefined) {
        newState.estimatedCost = progress.estimated_cost;
      }
      if (progress.api_calls_made !== undefined) {
        newState.apiCallsMade = progress.api_calls_made;
      }
      
      // Update current stage based on backend stage name
      if (progress.stage) {
        newState.currentStage = progress.stage;
      }
      
      // Handle completion
      if (progress.status === 'completed') {
        newState.status = 'completed';
        newState.currentStage = null;
        
        // Update final metrics and duration - try multiple possible fields
        if (progress.final_metrics) {
          newState.tokensUsed = progress.final_metrics.total_tokens || newState.tokensUsed;
          newState.estimatedCost = progress.final_metrics.total_cost || newState.estimatedCost;
          newState.apiCallsMade = progress.final_metrics.total_api_calls || newState.apiCallsMade;
          
          // Try to get duration from final_metrics
          newState.duration = progress.final_metrics.total_duration || 
                              progress.final_metrics.duration ||
                              progress.final_metrics.elapsed_time;
        }
        
        // Also try to get duration from other progress fields if not found in final_metrics
        if (!newState.duration) {
          newState.duration = progress.total_duration || 
                              progress.elapsed_time || 
                              progress.duration ||
                              progress.current_duration ||
                              progress.research_duration ||
                              progress.time_elapsed;
        }
        
        // If we still don't have duration, calculate it from start time
        if (!newState.duration && action.researchStartTime) {
          const elapsedSeconds = (Date.now() - action.researchStartTime) / 1000;
          newState.duration = `${elapsedSeconds.toFixed(1)}s`;
        }
      }
      
      // Handle errors
      if (progress.status === 'error') {
        newState.status = 'failed';
        newState.error = progress.message || 'Research failed';
        newState.currentStage = null;
      }
      
      return newState;
    
    case ActionTypes.RESEARCH_COMPLETED:
      return {
        ...state,
        status: 'completed',
        results: action.results,
        stages: state.stages.map(s => ({ ...s, status: 'completed' })),
        currentStage: null
      };
    
    case ActionTypes.RESEARCH_FAILED:
      return {
        ...state,
        status: 'failed',
        error: action.error,
        currentStage: null
      };
    
    case ActionTypes.SET_QUERY:
      return { ...state, query: action.query };
    
    case ActionTypes.SET_MAX_QUESTIONS:
      return { ...state, maxQuestions: action.maxQuestions };
    
    case ActionTypes.SET_RESULTS:
      return { ...state, results: action.results };
    
    case ActionTypes.SET_METRICS:
      return { ...state, metrics: action.metrics };
    
    case ActionTypes.SET_SESSION:
      return { ...state, currentSession: action.sessionId };
    
    case ActionTypes.TOGGLE_ARCHITECTURE:
      return { ...state, showArchitecture: !state.showArchitecture };
    
    case ActionTypes.TOGGLE_API_CONFIG:
      return { ...state, showApiConfig: !state.showApiConfig };
    
    case ActionTypes.TOGGLE_MODEL_CONFIG:
      return { ...state, showModelConfig: !state.showModelConfig };
    
    case ActionTypes.SET_ERROR:
      return { ...state, error: action.error };
    
    case ActionTypes.CLEAR_ERROR:
      return { ...state, error: null };
    
    case ActionTypes.WEBSOCKET_CONNECTED:
      return { ...state, isConnected: true };
    
    case ActionTypes.WEBSOCKET_DISCONNECTED:
      return { ...state, isConnected: false };
    
    case ActionTypes.RESET_RESEARCH:
      return {
        ...initialState,
        query: state.query,
        maxQuestions: state.maxQuestions,
        showArchitecture: state.showArchitecture,
        showApiConfig: state.showApiConfig,
        showModelConfig: state.showModelConfig
      };
    
    default:
      return state;
  }
};

// Create context
const ResearchContext = createContext();

// Provider component
export const ResearchProvider = ({ children }) => {
  const [state, dispatch] = useReducer(researchReducer, initialState);
  const wsRef = useRef(null);
  const researchStartTimeRef = useRef(null);
  
  // Create enhanced dispatch that has access to refs
  const enhancedDispatch = useCallback((action) => {
    if (action.type === ActionTypes.UPDATE_PROGRESS) {
      // Add researchStartTime to the action so reducer can access it
      action.researchStartTime = researchStartTimeRef.current;
    }
    dispatch(action);
  }, []);
  
  // Action creators
  const actions = {
    setQuery: useCallback((query) => {
      enhancedDispatch({ type: ActionTypes.SET_QUERY, query });
    }, [enhancedDispatch]),
    
    setMaxQuestions: useCallback((maxQuestions) => {
      enhancedDispatch({ type: ActionTypes.SET_MAX_QUESTIONS, maxQuestions });
    }, [enhancedDispatch]),
    
    toggleArchitecture: useCallback(() => {
      enhancedDispatch({ type: ActionTypes.TOGGLE_ARCHITECTURE });
    }, [enhancedDispatch]),
    
    toggleApiConfig: useCallback(() => {
      enhancedDispatch({ type: ActionTypes.TOGGLE_API_CONFIG });
    }, [enhancedDispatch]),
    
    toggleModelConfig: useCallback(() => {
      enhancedDispatch({ type: ActionTypes.TOGGLE_MODEL_CONFIG });
    }, [enhancedDispatch]),
    
    setError: useCallback((error) => {
      enhancedDispatch({ type: ActionTypes.SET_ERROR, error });
    }, [enhancedDispatch]),
    
    clearError: useCallback(() => {
      enhancedDispatch({ type: ActionTypes.CLEAR_ERROR });
    }, [enhancedDispatch]),
    
    setMetrics: useCallback((metrics) => {
      enhancedDispatch({ type: ActionTypes.SET_METRICS, metrics });
    }, [enhancedDispatch]),
    
    startResearch: useCallback(async (modelConfig, agentModels) => {
      if (!state.query || !state.query.trim()) {
        enhancedDispatch({ type: ActionTypes.SET_ERROR, error: '⚠️ Please enter a research query' });
        return;
      }

      const trimmedQuery = state.query.trim();
      if (trimmedQuery.length < 3) {
        enhancedDispatch({ type: ActionTypes.SET_ERROR, error: `⚠️ Query must be at least 3 characters long. You entered: '${trimmedQuery}' (${trimmedQuery.length} characters)` });
        return;
      }

      if (trimmedQuery.length > 1000) {
        enhancedDispatch({ type: ActionTypes.SET_ERROR, error: `⚠️ Query must be no more than 1000 characters long. You entered ${trimmedQuery.length} characters` });
        return;
      }
      
      try {
        const request = {
          query: trimmedQuery,
          max_questions: state.maxQuestions,
          selected_model: modelConfig?.default_model || 'accounts/fireworks/models/llama-v3p1-405b-instruct',
          agent_models: agentModels,
          executive_summary_style: 'comprehensive',
          output_format: 'json',
          save_session: true
        };
        
        enhancedDispatch({ type: ActionTypes.START_RESEARCH });
        researchStartTimeRef.current = Date.now();
        
        const data = await api.startResearch(request);
        
        if (data.session_id) {
          enhancedDispatch({ type: ActionTypes.SET_SESSION, sessionId: data.session_id });
          
          // Connect WebSocket for real-time updates
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const wsUrl = `${protocol}//${window.location.host}/ws/${data.session_id}`;
          
          if (wsRef.current) {
            wsRef.current.close();
          }
          
          wsRef.current = createWebSocketConnection(data.session_id, {
            onMessage: (progress) => {
              enhancedDispatch({ type: ActionTypes.UPDATE_PROGRESS, progress });
              
              if (progress.status === 'completed') {
                // Fetch final results
                api.getResults(data.session_id).then(results => {
                  enhancedDispatch({ type: ActionTypes.SET_RESULTS, results });
                }).catch(console.error);
                
                // Fetch metrics
                api.getMetrics(data.session_id).then(metricsData => {
                  if (metricsData.success && metricsData.metrics) {
                    enhancedDispatch({ type: ActionTypes.SET_METRICS, metrics: metricsData.metrics });
                  }
                }).catch(console.error);
              }
            },
            onOpen: () => {
              enhancedDispatch({ type: ActionTypes.WEBSOCKET_CONNECTED });
            },
            onClose: () => {
              enhancedDispatch({ type: ActionTypes.WEBSOCKET_DISCONNECTED });
            },
            onError: (error) => {
              enhancedDispatch({ type: ActionTypes.WEBSOCKET_DISCONNECTED });
              enhancedDispatch({ type: ActionTypes.SET_ERROR, error: 'WebSocket connection failed' });
            }
          });
        } else {
          enhancedDispatch({ type: ActionTypes.RESEARCH_FAILED, error: data.message });
        }
      } catch (error) {
        enhancedDispatch({ type: ActionTypes.RESEARCH_FAILED, error: error.message || 'Failed to start research' });
      }
    }, [state.query, state.maxQuestions, enhancedDispatch]),
    
    resetResearch: useCallback(() => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      researchStartTimeRef.current = null;
      enhancedDispatch({ type: ActionTypes.RESET_RESEARCH });
    }, [enhancedDispatch])
  };
  
  // Calculate real-time duration
  const getRealTimeDuration = useCallback(() => {
    if (!researchStartTimeRef.current) return null;
    
    if (state.status === 'completed' && state.duration) {
      return typeof state.duration === 'string' ? state.duration : `${state.duration.toFixed(1)}s`;
    }
    
    if (state.status === 'researching') {
      const elapsed = (Date.now() - researchStartTimeRef.current) / 1000;
      return `${elapsed.toFixed(1)}s`;
    }
    
    return null;
  }, [state.status, state.duration]);
  
  const value = {
    state,
    actions,
    getRealTimeDuration,
    // Computed values for backward compatibility
    isResearching: state.status === 'researching',
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed'
  };
  
  return (
    <ResearchContext.Provider value={value}>
      {children}
    </ResearchContext.Provider>
  );
};

// Hook to use research context
export const useResearchContext = () => {
  const context = useContext(ResearchContext);
  if (!context) {
    throw new Error('useResearchContext must be used within a ResearchProvider');
  }
  return context;
};

export { ActionTypes }; 