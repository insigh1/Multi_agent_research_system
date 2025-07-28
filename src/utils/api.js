// API utility functions
const API_BASE = '';

export const api = {
  async startResearch(request) {
    const response = await fetch('/api/research/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return response.json();
  },

  async getResults(sessionId) {
    const response = await fetch(`/api/research/${sessionId}/results`);
    return response.json();
  },

  async getMetrics(sessionId) {
    const response = await fetch(`/api/research/${sessionId}/metrics`);
    return response.json();
  },

  async getModels() {
    const response = await fetch('/api/models');
    return response.json();
  },

  async getModelConfig() {
    const response = await fetch('/api/models/config');
    return response.json();
  },

  async updateModelConfig(agentModels) {
    const response = await fetch('/api/models/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_models: agentModels })
    });
    return response.json();
  }
};

export const createSSEConnection = (sessionId, callbacks) => {
  const sseUrl = `/api/events/${sessionId}`;
  
  console.log('Connecting to SSE:', sseUrl);
  const eventSource = new EventSource(sseUrl);
  
  eventSource.onopen = () => {
    console.log('SSE connected successfully');
    callbacks.onOpen?.();
  };
  
  eventSource.onmessage = (event) => {
    console.log('SSE message received:', event.data);
    try {
      const data = JSON.parse(event.data);
      
      // Handle close message
      if (data.type === 'close') {
        eventSource.close();
        callbacks.onClose?.();
        return;
      }
      
      // Handle error message
      if (data.type === 'error') {
        console.error('SSE error received:', data.message);
        callbacks.onError?.(new Error(data.message));
        eventSource.close();
        return;
      }
      
      callbacks.onMessage?.(data);
    } catch (err) {
      console.error('Error parsing SSE message:', err);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    callbacks.onError?.(error);
    eventSource.close();
  };
  
  // Return an object with a close method for compatibility
  return {
    close: () => {
      eventSource.close();
    },
    readyState: eventSource.readyState,
    CONNECTING: EventSource.CONNECTING,
    OPEN: EventSource.OPEN,
    CLOSED: EventSource.CLOSED
  };
};

// Legacy WebSocket function - deprecated but kept for compatibility
export const createWebSocketConnection = (sessionId, callbacks) => {
  console.warn('WebSocket connection is deprecated. Please use createSSEConnection instead.');
  return createSSEConnection(sessionId, callbacks);
}; 