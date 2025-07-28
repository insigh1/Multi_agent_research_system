import React, { memo } from 'react';
import { PIPELINE_STEPS, AGENT_LIST, SYSTEM_COMPONENTS } from '../constants/constants';

const ArchitectureSidebar = memo(({ show, onToggle, progress }) => (
  <div className={`w-80 transition-all duration-300 ease-in-out ${show ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-full pointer-events-none'}`}>
    <div className="bg-white rounded-lg shadow-md p-4 h-fit">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-900">
          <i className="fas fa-network-wired text-blue-500 mr-2"></i>
          System Architecture
        </h2>
        <button
          onClick={onToggle}
          className="text-xs text-gray-500 hover:text-gray-700 flex items-center px-2 py-1 rounded hover:bg-gray-100 transition-colors"
        >
          <i className="fas fa-chevron-right mr-1"></i>
          Hide
        </button>
      </div>
      
      <div className="mb-4">
        <h3 className="text-xs font-medium text-gray-700 mb-2">
          <i className="fas fa-route text-indigo-500 mr-1"></i>
          Processing Pipeline
        </h3>
        <div className="space-y-1">
          {PIPELINE_STEPS.map((step, index) => {
            const isActive = progress && progress.stage === step.stage;
            // Check if stage is completed in stage_breakdown
            const isCompleted = progress && progress.stage_breakdown && 
              progress.stage_breakdown.find(s => s.name === step.stage)?.status === 'completed';
            
            return (
              <div key={index} className={`flex items-center space-x-2 p-2 rounded text-xs ${
                isActive ? 'bg-blue-50 border border-blue-200' :
                isCompleted ? 'bg-green-50 border border-green-200' :
                'bg-gray-50 border border-gray-100'
              }`}>
                <span className="text-sm">{step.icon}</span>
                <span className={`font-medium ${
                  isActive ? 'text-blue-700' :
                  isCompleted ? 'text-green-700' :
                  'text-gray-600'
                }`}>
                  {step.name}
                </span>
                {isActive && <i className="fas fa-spinner fa-spin text-blue-500 ml-auto"></i>}
                {isCompleted && <i className="fas fa-check text-green-500 ml-auto"></i>}
              </div>
            );
          })}
        </div>
      </div>
      
      <div className="mb-4">
        <h3 className="text-xs font-medium text-gray-700 mb-2">
          <i className="fas fa-users text-purple-500 mr-1"></i>
          AI Agents
        </h3>
        <div className="space-y-1">
          {AGENT_LIST.map((agent, idx) => (
            <div key={idx} className="flex items-center space-x-2 p-1.5 bg-gray-50 rounded text-xs">
              <span>{agent.icon}</span>
              <span className="text-gray-700 font-medium">{agent.name}</span>
            </div>
          ))}
        </div>
      </div>
      
      <div>
        <h3 className="text-xs font-medium text-gray-700 mb-2">
          <i className="fas fa-cogs text-blue-500 mr-1"></i>
          Components
        </h3>
        <div className="space-y-1">
          {SYSTEM_COMPONENTS.map((component, idx) => (
            <div key={idx} className="flex items-center space-x-2 p-1.5 bg-gray-50 rounded text-xs">
              <span>{component.icon}</span>
              <span className="text-gray-700 font-medium">{component.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
));

ArchitectureSidebar.displayName = 'ArchitectureSidebar';

export default ArchitectureSidebar; 