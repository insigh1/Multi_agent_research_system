import { useRef, useCallback, useState } from 'react';
import { createWebSocketConnection } from '../utils/api';

export const useWebSocket = () => {
  const wsRef = useRef(null);
  const [progress, setProgress] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback((sessionId, callbacks) => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    const wsCallbacks = {
      onMessage: (data) => {
        setProgress(data);
        callbacks?.onMessage?.(data);
      },
      onOpen: () => {
        setIsConnected(true);
        callbacks?.onOpen?.();
      },
      onClose: () => {
        setIsConnected(false);
        callbacks?.onClose?.();
      },
      onError: (error) => {
        setIsConnected(false);
        callbacks?.onError?.(error);
      }
    };
    
    wsRef.current = createWebSocketConnection(sessionId, wsCallbacks);
    return wsRef.current;
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setProgress(null);
  }, []);

  return { 
    connect, 
    disconnect, 
    progress, 
    isConnected,
    setProgress 
  };
}; 