import React, { memo } from 'react';
import { PIPELINE_STEPS } from '../constants/constants';

const PipelineFlow = memo(({ progress }) => (
  <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-6">
    {PIPELINE_STEPS.map((step, index) => {
      const isActive = progress && progress.stage === step.stage;
      
      // Check if stage is completed in stage_breakdown
      const isCompleted = progress && progress.stage_breakdown && 
        progress.stage_breakdown.find(s => s.name === step.stage)?.status === 'completed';
      
      return (
        <div key={step.name} className="relative">
          <div className={`p-4 rounded-lg border-2 transition-all duration-300 ${
            isActive ? 'border-blue-500 bg-blue-100 shadow-md transform scale-105' :
            isCompleted ? 'border-green-500 bg-green-50' :
            'border-gray-300 bg-white hover:bg-gray-50'
          }`}>
            <div className="text-center">
              <div className={`text-3xl mb-2 ${isActive ? 'animate-bounce' : ''}`}>
                {step.icon}
              </div>
              <div className={`font-bold text-sm mb-1 ${
                isActive ? 'text-blue-700' :
                isCompleted ? 'text-green-700' :
                'text-gray-600'
              }`}>
                {step.name}
              </div>
              <div className="text-xs text-gray-500 mb-2 leading-tight">
                {step.description}
              </div>
              <div className="text-xs text-gray-400 font-mono">
                {step.agent}
              </div>
              {isCompleted && (
                <div className="text-green-600 text-lg mt-2">
                  <i className="fas fa-check-circle"></i>
                </div>
              )}
              {isActive && (
                <div className="text-blue-600 text-lg mt-2">
                  <i className="fas fa-spinner fa-spin"></i>
                </div>
              )}
            </div>
          </div>
          {index < 4 && (
            <div className="hidden md:block absolute top-1/2 -right-2 transform -translate-y-1/2 z-10">
              <div className={`w-0 h-0 border-l-[8px] border-r-[8px] border-t-[6px] border-l-transparent border-r-transparent ${
                isCompleted ? 'border-t-green-500' : 'border-t-gray-300'
              }`}></div>
            </div>
          )}
        </div>
      );
    })}
  </div>
));

PipelineFlow.displayName = 'PipelineFlow';

export default PipelineFlow; 