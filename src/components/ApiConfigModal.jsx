import React, { memo, useCallback, useState } from 'react';

const ApiConfigModal = memo(({ show, onClose, apiKeys, setApiKeys }) => {
  const [searchEngine, setSearchEngine] = useState(() => {
    return localStorage.getItem('preferredSearchEngine') || 'firecrawl';
  });

  const saveApiKeys = useCallback(() => {
    localStorage.setItem('apiKeys', JSON.stringify(apiKeys));
    localStorage.setItem('preferredSearchEngine', searchEngine);
    onClose();
  }, [apiKeys, searchEngine, onClose]);
  
  if (!show) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 p-2 pt-4 pb-4 overflow-hidden">
      <div className="bg-white rounded-lg w-full max-w-lg max-h-full flex flex-col shadow-2xl min-h-0">
        {/* Fixed Header */}
        <div className="p-6 pb-4 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">API Configuration</h3>
              <p className="text-sm text-gray-600">Configure your API keys for research</p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <i className="fas fa-times text-lg"></i>
            </button>
          </div>
        </div>
        
        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6" style={{scrollbarGutter: 'stable'}}>
          <div className="space-y-6">
            {/* Fireworks AI API Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Fireworks AI API Key (Required)
              </label>
              <input
                type="password"
                value={apiKeys.fireworks}
                onChange={(e) => setApiKeys(prev => ({ ...prev, fireworks: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your Fireworks AI API key"
              />
            </div>

            {/* Search Engine Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Preferred Search Engine
              </label>
              <select
                value={searchEngine}
                onChange={(e) => setSearchEngine(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="firecrawl">Firecrawl (Preferred - Full Content)</option>
                <option value="brave">Brave Search (Fast Snippets)</option>
                <option value="auto">Auto (Try Firecrawl, fallback to Brave)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Firecrawl provides full content extraction for better quality evaluation
              </p>
            </div>

            {/* Firecrawl API Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Firecrawl API Key {searchEngine === 'brave' ? '(Optional)' : '(Recommended)'}
              </label>
              <input
                type="password"
                value={apiKeys.firecrawl}
                onChange={(e) => setApiKeys(prev => ({ ...prev, firecrawl: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your Firecrawl API key"
              />
              <p className="text-xs text-gray-500 mt-1">
                Get your key from <a href="https://firecrawl.dev" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800">firecrawl.dev</a>
              </p>
            </div>
            
            {/* Brave Search API Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Brave Search API Key {searchEngine === 'firecrawl' ? '(Fallback)' : '(Required)'}
              </label>
              <input
                type="password"
                value={apiKeys.brave}
                onChange={(e) => setApiKeys(prev => ({ ...prev, brave: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your Brave Search API key"
              />
              <p className="text-xs text-gray-500 mt-1">
                Get your key from <a href="https://brave.com/search/api" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800">brave.com/search/api</a>
              </p>
            </div>
          </div>
        </div>
        
        {/* Fixed Footer */}
        <div className="p-6 pt-4 border-t border-gray-200 flex-shrink-0">
          <div className="flex justify-end space-x-3">
            <button 
              onClick={onClose} 
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button 
              onClick={saveApiKeys} 
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

ApiConfigModal.displayName = 'ApiConfigModal';

export default ApiConfigModal; 