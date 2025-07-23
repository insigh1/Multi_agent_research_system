import React, { memo } from 'react';

const ModelConfigModal = memo(({ show, onClose, modelConfig, agentModels, availableModels, updateAgentModel, saveModelConfig, applyModelPreset }) => {
  if (!show) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 p-2 pt-4 pb-4 overflow-hidden">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-full flex flex-col shadow-2xl min-h-0">
        {/* Fixed Header */}
        <div className="p-4 pb-3 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Agent Model Configuration</h3>
              <p className="text-xs text-gray-600">Configure AI models for optimal performance</p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <i className="fas fa-times text-lg"></i>
            </button>
          </div>
        </div>
        
        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4" style={{scrollbarGutter: 'stable'}}>
          {modelConfig && modelConfig.agent_assignments ? (
            <div className="space-y-6">
              {/* Model Presets */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <i className="fas fa-magic mr-2 text-purple-500"></i>
                  Quick Model Presets
                </h4>
                <p className="text-xs text-gray-600 mb-3">
                  Choose a preset to automatically configure optimal models for each agent based on their specific tasks.
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <button
                    onClick={() => {
                      console.log('🖱️ Modal Budget preset clicked');
                      applyModelPreset && applyModelPreset('budget');
                    }}
                    className="px-3 py-2 text-sm bg-green-50 border border-green-200 text-green-700 rounded-md hover:bg-green-100 transition-colors flex items-center justify-center"
                    title="Cost-effective models optimized for each agent task"
                  >
                    <i className="fas fa-piggy-bank mr-2"></i>
                    Budget
                  </button>
                  <button
                    onClick={() => {
                      console.log('🖱️ Modal Balanced preset clicked');
                      applyModelPreset && applyModelPreset('balanced');
                    }}
                    className="px-3 py-2 text-sm bg-blue-50 border border-blue-200 text-blue-700 rounded-md hover:bg-blue-100 transition-colors flex items-center justify-center"
                    title="Good balance of cost and performance with task specialization"
                  >
                    <i className="fas fa-balance-scale mr-2"></i>
                    Balanced
                  </button>
                  <button
                    onClick={() => {
                      console.log('🖱️ Modal Performance preset clicked');
                      applyModelPreset && applyModelPreset('performance');
                    }}
                    className="px-3 py-2 text-sm bg-purple-50 border border-purple-200 text-purple-700 rounded-md hover:bg-purple-100 transition-colors flex items-center justify-center"
                    title="High-quality models specialized for each agent's role"
                  >
                    <i className="fas fa-rocket mr-2"></i>
                    Performance
                  </button>
                  <button
                    onClick={() => {
                      console.log('🖱️ Modal Premium preset clicked');
                      applyModelPreset && applyModelPreset('premium');
                    }}
                    className="px-3 py-2 text-sm bg-rose-50 border border-rose-200 text-rose-700 rounded-md hover:bg-rose-100 transition-colors flex items-center justify-center"
                    title="Best available models for maximum quality results"
                  >
                    <i className="fas fa-crown mr-2"></i>
                    Premium
                  </button>
                </div>
              </div>
              {/* Current Configuration Overview */}
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <h4 className="text-sm font-semibold text-blue-800 mb-2 flex items-center">
                  <i className="fas fa-info-circle mr-2"></i>
                  Current Configuration
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                  <div>
                    <span className="font-medium text-blue-700">Budget Limit:</span>
                    <div className="text-blue-800">${modelConfig.budget_limit}/query</div>
                  </div>
                  <div>
                    <span className="font-medium text-blue-700">Total Agents:</span>
                    <div className="text-blue-800">{modelConfig.agent_assignments.length}</div>
                  </div>
                  <div>
                    <span className="font-medium text-blue-700">Available Models:</span>
                    <div className="text-blue-800">{modelConfig.available_models.length}</div>
                  </div>
                </div>
              </div>
              
              {/* Agent Model Assignments */}
              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <i className="fas fa-robot mr-2 text-purple-600"></i>
                  Agent Model Assignments
                </h4>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {modelConfig.agent_assignments.map((agent, index) => (
                    <div key={agent.agent_type} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h5 className="font-semibold text-gray-900 capitalize">
                            {agent.agent_type.replace('_', ' ')} Agent
                          </h5>
                          <p className="text-xs text-gray-600">{agent.description}</p>
                        </div>
                        <div className="text-right text-xs text-gray-500">
                          <div>Max: {agent.max_tokens} tokens</div>
                          <div>Temp: {agent.temperature}</div>
                        </div>
                      </div>
                      
                      <div className="mb-3">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Select Model
                        </label>
                        <select
                          value={agentModels[agent.agent_type] || agent.model_name}
                          onChange={(e) => updateAgentModel(agent.agent_type, e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
                        >
                          {modelConfig.available_models.map(model => (
                            <option key={model} value={model}>
                              {model}
                            </option>
                          ))}
                        </select>
                      </div>
                      
                      {/* Model pricing info */}
                      {(() => {
                        const selectedModel = agentModels[agent.agent_type] || agent.model_name;
                        const pricing = modelConfig.model_pricing[selectedModel];
                        return pricing ? (
                          <div className="bg-white rounded p-2 border border-gray-200">
                            <div className="text-xs text-gray-600">
                              <div className="flex justify-between">
                                <span>Input:</span>
                                <span className="font-mono">${pricing.input}/1M tokens</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Output:</span>
                                <span className="font-mono">${pricing.output}/1M tokens</span>
                              </div>
                            </div>
                          </div>
                        ) : null;
                      })()}
                    </div>
                  ))}
                </div>
              </div>
              

            </div>
          ) : (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-4"></div>
              <div className="text-gray-600">Loading model configuration...</div>
            </div>
          )}
        </div>
        
        {/* Fixed Footer */}
        <div className="p-4 pt-3 border-t border-gray-200 flex-shrink-0">
          <div className="flex justify-end space-x-3">
            <button 
              onClick={onClose} 
              className="px-6 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button 
              onClick={saveModelConfig} 
              className="px-6 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors flex items-center"
            >
              <i className="fas fa-save mr-2"></i>
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

ModelConfigModal.displayName = 'ModelConfigModal';

export default ModelConfigModal; 