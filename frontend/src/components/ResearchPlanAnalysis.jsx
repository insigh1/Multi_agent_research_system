import React, { memo } from 'react';

const ResearchPlanAnalysis = memo(({ progress }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-4 h-80 overflow-y-auto scrollbar-thin">
    <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
      <i className="fas fa-brain text-indigo-500 mr-2"></i>
      AI Research Plan Analysis
    </h4>
    
    {/* Research Query Display */}
    <div className="bg-gray-50 rounded-lg p-3 mb-3">
      <div className="text-sm text-gray-600 mb-1">Research Query:</div>
      <div className="text-sm font-medium text-gray-800 italic">
        "{progress?.research_plan?.main_query || window.currentQuery || 'Loading...'}"
      </div>
    </div>
    
    {/* Research Strategy */}
    {progress?.research_plan?.research_strategy && (
      <div className="bg-indigo-50 rounded-lg p-3 mb-3 border border-indigo-200">
        <div className="text-sm font-semibold text-indigo-700 mb-2 flex items-center">
          <i className="fas fa-lightbulb mr-1"></i>
          AI Research Strategy
        </div>
        <div className="text-sm text-gray-700">
          {progress.research_plan.research_strategy}
        </div>
      </div>
    )}
    
    {/* Research Insights Grid */}
    {progress?.research_plan ? (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <div className="bg-blue-50 rounded-lg p-3">
          <div className="text-xs font-semibold text-blue-700 mb-2">
            <i className="fas fa-brain mr-1"></i>
            Research Complexity
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-bold text-blue-800">
                Level {progress.research_plan.estimated_complexity}/5
              </div>
              <div className="text-xs text-blue-600">
                Est. {Math.round(progress.research_plan.estimated_duration || 0)}min
              </div>
            </div>
            <div className="text-lg">
              {progress.research_plan.estimated_complexity <= 2 ? '🟢' : 
               progress.research_plan.estimated_complexity <= 3 ? '🟡' : '🔴'}
            </div>
          </div>
        </div>
        
        <div className="bg-green-50 rounded-lg p-3">
          <div className="text-xs font-semibold text-green-700 mb-2">
            <i className="fas fa-tags mr-1"></i>
            Research Categories
          </div>
          <div className="flex flex-wrap gap-1">
            {(progress.research_plan.categories || []).map((category, idx) => (
              <span key={idx} className="inline-block bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full">
                {category}
              </span>
            ))}
          </div>
        </div>
        
        <div className="bg-purple-50 rounded-lg p-3">
          <div className="text-xs font-semibold text-purple-700 mb-2">
            <i className="fas fa-list-ol mr-1"></i>
            Sub-Questions
          </div>
          <div className="text-lg font-bold text-purple-800">
            {progress.research_plan.sub_questions?.length || 0}
          </div>
          <div className="text-xs text-purple-600">AI-generated</div>
        </div>
      </div>
    ) : (
      <div className="bg-gray-50 rounded-lg p-4 text-center">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto mb-2"></div>
        <div className="text-sm text-gray-600">AI is analyzing your query...</div>
        <div className="text-xs text-gray-500">Generating research strategy and sub-questions</div>
      </div>
    )}
    
    {/* Dynamic Sub-Questions Display */}
    {progress?.research_plan?.sub_questions && progress.research_plan.sub_questions.length > 0 && (
      <div className="bg-indigo-50 rounded-lg p-3 border border-indigo-200">
        <div className="text-sm font-semibold text-indigo-700 mb-3 flex items-center">
          <i className="fas fa-list-ol mr-1"></i>
          AI-Generated Research Questions ({progress.research_plan.sub_questions.length})
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto scrollbar-thin">
          {progress.research_plan.sub_questions.map((sq, idx) => (
            <div key={idx} className="bg-white rounded-lg p-3 border border-indigo-100 shadow-sm">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-800 mb-1">
                    <span className="bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full text-xs font-bold mr-2">
                      {sq.id}
                    </span>
                    {sq.question}
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className={`px-2 py-1 rounded-full font-medium ${
                      sq.priority === 1 ? 'bg-red-100 text-red-700' :
                      sq.priority === 2 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      Priority {sq.priority}
                    </span>
                    <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-medium">
                      {sq.category}
                    </span>
                  </div>
                  {sq.search_terms && sq.search_terms.length > 0 && (
                    <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-2">
                      <i className="fas fa-search mr-1"></i>
                      <strong>Search Terms:</strong> {sq.search_terms.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
));

ResearchPlanAnalysis.displayName = 'ResearchPlanAnalysis';

export default ResearchPlanAnalysis; 