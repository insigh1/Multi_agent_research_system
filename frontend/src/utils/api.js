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

export const createWebSocketConnection = (sessionId, callbacks) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;
  
  console.log('Connecting to WebSocket:', wsUrl);
  const ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    console.log('WebSocket connected successfully');
    callbacks.onOpen?.();
  };
  
  ws.onmessage = (event) => {
    console.log('WebSocket message received:', event.data);
    try {
      const data = JSON.parse(event.data);
      callbacks.onMessage?.(data);
    } catch (err) {
      console.error('Error parsing WebSocket message:', err);
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    callbacks.onError?.(error);
  };
  
  ws.onclose = (event) => {
    console.log('WebSocket disconnected:', event.code, event.reason);
    callbacks.onClose?.(event);
  };
  
  return ws;
}; 