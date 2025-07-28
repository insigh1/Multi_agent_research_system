import { useRef, useCallback, useState } from 'react';
import { createSSEConnection } from '../utils/api';

export const useWebSocket = () => {
  const sseRef = useRef(null);
  const [progress, setProgress] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback((sessionId, callbacks) => {
    // Close existing connection if any
    if (sseRef.current) {
      sseRef.current.close();
    }
    
    const sseCallbacks = {
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
    
    sseRef.current = createSSEConnection(sessionId, sseCallbacks);
    return sseRef.current;
  }, []);

  const disconnect = useCallback(() => {
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
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