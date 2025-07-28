import React, { useState, useCallback, useEffect } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import PipelineFlow from './components/PipelineFlow';

import ApiConfigModal from './components/ApiConfigModal';
import ModelConfigModal from './components/ModelConfigModal';
import ArchitectureSidebar from './components/ArchitectureSidebar';
import { useWebSocket } from './hooks/useWebSocket';
import { useResearch } from './hooks/useResearch';
import { useModelConfig } from './hooks/useModelConfig';
import { useResearchContext } from './context/ResearchContext';

// Source Card Component for Information Gathering
const SourceCard = ({ source, index }) => {
  const [isContentExpanded, setIsContentExpanded] = useState(false);
  
  const truncateText = (text, maxLength = 150) => {
    if (!text) return '';
    
    // Clean up the text by removing markdown/HTML elements and metadata
    let cleanText = text
      // Remove markdown image syntax ![alt](url)
      .replace(/!\[.*?\]\(.*?\)/g, '')
      // Remove markdown links [text](url) but keep the text
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      // Remove HTML tags
      .replace(/<[^>]*>/g, '')
      // Remove date patterns like "2025-01-0808 January 2025"
      .replace(/\d{4}-\d{2}-\d{2}\d{2}\s+\w+\s+\d{4}/g, '')
      // Remove "Last updated:" patterns
      .replace(/Last updated:\s*/gi, '')
      // Remove markdown headers (# ## ###)
      .replace(/^#+\s*/gm, '')
      // Remove extra whitespace and newlines
      .replace(/\s+/g, ' ')
      .trim();
    
    // If the text starts with date/metadata, try to find the first real sentence
    const sentences = cleanText.split(/[.!?]+/).filter(s => s.trim().length > 20);
    if (sentences.length > 0) {
      cleanText = sentences[0].trim() + (sentences.length > 1 ? '...' : '.');
    }
    
    return cleanText.length > maxLength ? cleanText.substring(0, maxLength) + '...' : cleanText;
  };



  const formatUrl = (url) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace('www.', '');
    } catch {
      return url;
    }
  };

  return (
    <div className="bg-white rounded-lg border border-emerald-100 shadow-sm">
      {/* Source Header */}
      <div 
        className="flex items-start justify-between p-3 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsContentExpanded(!isContentExpanded)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <div className="flex items-center justify-center w-6 h-6 bg-emerald-100 text-emerald-600 rounded-full text-xs font-bold">
              {index + 1}
            </div>
            <div className="text-sm font-medium text-gray-800 truncate">
              {source.title || formatUrl(source.url)}
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <i className="fas fa-link text-emerald-500"></i>
            <a 
              href={source.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline truncate max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              {source.url}
            </a>
            {source.relevance_score && (
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                source.relevance_score >= 0.8 ? 'bg-green-100 text-green-700' :
                source.relevance_score >= 0.6 ? 'bg-yellow-100 text-yellow-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {Math.round(source.relevance_score * 100)}% relevant
              </span>
            )}
          </div>
          
          {/* Snippet Preview */}
          {(source.content || source.snippet || source.description) && (
            <div className="mt-2 text-xs text-gray-700 leading-relaxed bg-gradient-to-r from-blue-50 to-indigo-50 px-3 py-2 rounded-md border border-blue-100 italic">
              "{truncateText(source.content || source.snippet || source.description, 180)}"
            </div>
          )}


        </div>
        <div className="flex-shrink-0 ml-2">
          <i className={`fas fa-chevron-${isContentExpanded ? 'up' : 'down'} text-xs text-gray-400 transition-transform`}></i>
        </div>
      </div>

      {/* Expandable Content */}
      {isContentExpanded && (
        <div className="border-t bg-gray-50 p-3">
          <div className="space-y-3">
            {/* Main Content - Make this the primary focus */}
            {(source.content || source.snippet || source.description) && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-1">
                  Full Content {source.source_type && `(${source.source_type === 'firecrawl' ? 'Firecrawl' : 'Brave Search'})`}:
                </div>
                <div className="text-xs text-gray-700 bg-white rounded p-3 border border-gray-200 max-h-64 overflow-y-auto scrollbar-thin">
                  <div className="whitespace-pre-wrap leading-relaxed">{source.content || source.snippet || source.description}</div>
                </div>
                <div className="flex justify-end mt-2">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(source.content || source.snippet || source.description);
                      // You could add a toast notification here
                    }}
                    className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    <i className="fas fa-copy"></i>
                    Copy {source.source_type === 'firecrawl' ? 'Full Page Content' : 'Content'}
                  </button>
                </div>
              </div>
            )}
            
            {/* Source Metadata */}
            <div className="grid grid-cols-2 gap-3">
              {source.type && (
                <div>
                  <div className="text-xs font-medium text-gray-700 mb-1">Content Type:</div>
                  <div className="text-xs text-gray-600 bg-white rounded px-2 py-1 border border-gray-200">
                    {source.type}
                  </div>
                </div>
              )}
              {source.date && (
                <div>
                  <div className="text-xs font-medium text-gray-700 mb-1">Published:</div>
                  <div className="text-xs text-gray-600 bg-white rounded px-2 py-1 border border-gray-200">
                    {source.date}
                  </div>
                </div>
              )}
            </div>

            {/* Key Information */}
            {source.key_points && source.key_points.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-1">Key Points:</div>
                <div className="space-y-1">
                  {source.key_points.map((point, idx) => (
                    <div key={idx} className="text-xs text-gray-700 bg-white rounded p-2 border border-gray-200 flex items-start">
                      <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-2 mt-1.5 flex-shrink-0"></div>
                      <div>{point}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Source Actions */}
            {(source.content || source.snippet || source.description) && (
              <div className="flex items-center gap-2 pt-2 border-t border-gray-200">
                <button 
                  onClick={() => {
                    navigator.clipboard.writeText(source.content || source.snippet || source.description);
                    // Could add a toast notification here
                  }}
                  className="text-xs text-gray-600 hover:text-gray-800 flex items-center gap-1"
                >
                  <i className="fas fa-copy"></i>
                  <span>Copy {source.source_type === 'firecrawl' ? 'Full Page Content' : 'Content'}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Quality Evaluation Card Component
const QualityEvaluationCard = ({ evaluation, index }) => {
  const [isDetailsExpanded, setIsDetailsExpanded] = useState(false);
  
  const getGradeColor = (grade) => {
    switch (grade) {
      case 'A+':
      case 'A':
        return 'text-green-700 bg-green-100';
      case 'B+':
      case 'B':
        return 'text-blue-700 bg-blue-100';
      case 'C+':
      case 'C':
        return 'text-yellow-700 bg-yellow-100';
      case 'D':
        return 'text-orange-700 bg-orange-100';
      case 'F':
        return 'text-red-700 bg-red-100';
      default:
        return 'text-gray-700 bg-gray-100';
    }
  };
  
  const getPassFailColor = (status) => {
    return status === 'PASS' ? 'text-green-700 bg-green-100' : 'text-red-700 bg-red-100';
  };
  
  const formatScore = (score) => {
    return (score * 100).toFixed(0) + '%';
  };

  return (
    <div className="bg-white rounded-lg border border-amber-100 shadow-sm">
      {/* Evaluation Header */}
      <div 
        className="flex items-start justify-between p-3 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsDetailsExpanded(!isDetailsExpanded)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <div className="flex items-center justify-center w-6 h-6 bg-amber-100 text-amber-600 rounded-full text-xs font-bold">
              {index + 1}
            </div>
            <div className="text-sm font-medium text-gray-800 truncate">
              {evaluation.sub_question}
            </div>
          </div>
          
          <div className="flex items-center gap-2 text-xs mb-2">
            <span className={`px-2 py-1 rounded-full text-xs font-bold ${getPassFailColor(evaluation.pass_fail_status)}`}>
              {evaluation.pass_fail_status}
            </span>
            <span className={`px-2 py-1 rounded-full text-xs font-bold ${getGradeColor(evaluation.quality_grade)}`}>
              Grade: {evaluation.quality_grade}
            </span>
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
              {formatScore(evaluation.overall_confidence)} confidence
            </span>
          </div>
          
          {/* Quick metrics */}
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span>
              <i className="fas fa-link mr-1"></i>
              {evaluation.sources_evaluated} sources
            </span>
            <span>
              <i className="fas fa-lightbulb mr-1"></i>
              {evaluation.insights_found} insights
            </span>
            <span>
              <i className="fas fa-check mr-1"></i>
              {evaluation.facts_extracted} facts
            </span>
          </div>
        </div>
        <div className="flex-shrink-0 ml-2">
          <i className={`fas fa-chevron-${isDetailsExpanded ? 'up' : 'down'} text-xs text-gray-400 transition-transform`}></i>
        </div>
      </div>

      {/* Expandable Content */}
      {isDetailsExpanded && (
        <div className="border-t bg-gray-50 p-3">
          <div className="space-y-4">
            {/* Score Breakdown */}
            <div>
              <div className="text-xs font-medium text-gray-700 mb-2">Quality Score Breakdown:</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                <div className="bg-white rounded p-2 border">
                  <div className="text-xs text-gray-600">Relevance</div>
                  <div className="text-sm font-bold text-gray-800">{formatScore(evaluation.relevance_score)}</div>
                </div>
                <div className="bg-white rounded p-2 border">
                  <div className="text-xs text-gray-600">Authority</div>
                  <div className="text-sm font-bold text-gray-800">{formatScore(evaluation.authority_score)}</div>
                </div>
                <div className="bg-white rounded p-2 border">
                  <div className="text-xs text-gray-600">Completeness</div>
                  <div className="text-sm font-bold text-gray-800">{formatScore(evaluation.completeness_score)}</div>
                </div>
                <div className="bg-white rounded p-2 border">
                  <div className="text-xs text-gray-600">Recency</div>
                  <div className="text-sm font-bold text-gray-800">{formatScore(evaluation.recency_score)}</div>
                </div>
                <div className="bg-white rounded p-2 border">
                  <div className="text-xs text-gray-600">Consistency</div>
                  <div className="text-sm font-bold text-gray-800">{formatScore(evaluation.consistency_score)}</div>
                </div>
                <div className="bg-white rounded p-2 border">
                  <div className="text-xs text-gray-600">Overall</div>
                  <div className={`text-sm font-bold ${evaluation.overall_confidence >= 0.6 ? 'text-green-800' : 'text-red-800'}`}>
                    {formatScore(evaluation.overall_confidence)}
                  </div>
                </div>
              </div>
            </div>
            
            {/* Assessment Reasoning */}
            {evaluation.assessment_reasoning && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-1">AI Assessment Reasoning:</div>
                <div className="text-xs text-gray-700 bg-white rounded p-3 border border-gray-200">
                  <div className="whitespace-pre-wrap leading-relaxed">{evaluation.assessment_reasoning}</div>
                </div>
              </div>
            )}
            
            {/* Quality Feedback */}
            {evaluation.quality_feedback && evaluation.quality_feedback.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-1">Quality Feedback:</div>
                <div className="space-y-1">
                  {evaluation.quality_feedback.map((feedback, idx) => (
                    <div key={idx} className="text-xs text-gray-700 bg-white rounded p-2 border border-gray-200 flex items-start">
                      <div className="w-1.5 h-1.5 bg-amber-500 rounded-full mr-2 mt-1.5 flex-shrink-0"></div>
                      <div>{feedback}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Improvement Suggestions */}
            {evaluation.improvement_suggestions && evaluation.improvement_suggestions.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-1">Improvement Suggestions:</div>
                <div className="space-y-1">
                  {evaluation.improvement_suggestions.map((suggestion, idx) => (
                    <div key={idx} className="text-xs text-gray-700 bg-blue-50 rounded p-2 border border-blue-200 flex items-start">
                      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-2 mt-1.5 flex-shrink-0"></div>
                      <div>{suggestion}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Source Assessment Breakdown */}
            {evaluation.source_breakdown && evaluation.source_breakdown.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-2">Source Quality Breakdown:</div>
                <div className="space-y-2 max-h-48 overflow-y-auto scrollbar-thin">
                  {evaluation.source_breakdown.map((source, idx) => (
                    <div key={idx} className="bg-white rounded p-2 border border-gray-200">
                      <div className="flex items-center justify-between mb-1">
                        <div className="text-xs font-medium text-gray-800 truncate">
                          {source.title}
                        </div>
                        <div className={`text-xs px-2 py-1 rounded ${source.passed_quality ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {source.passed_quality ? 'PASS' : 'FAIL'}
                        </div>
                      </div>
                      <div className="text-xs text-blue-600 mb-1 truncate">{source.url}</div>
                      <div className="flex gap-2 text-xs">
                        <span>Auth: {formatScore(source.authority_score)}</span>
                        <span>Rel: {formatScore(source.relevance_score)}</span>
                        <span className="text-gray-500">{source.source_type}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Stage Card Component with Dropdown Details
const StageCard = ({ stage, stageIndex, progress }) => {
  const isResearchPlanningStage = stage.name === 'Research Planning';
  const isInformationGatheringStage = stage.name === 'Information Gathering';
  const isQualityEvaluationStage = stage.name === 'Quality Evaluation';
  const isContentSummarizationStage = stage.name === 'Content Summarization' || stage.name === 'content_summarization';
  const isReportAssemblyStage = stage.name === 'Report Assembly' || stage.name === 'Synthesis';
  const [isExpanded, setIsExpanded] = useState(false); // Default closed for cleaner interface - users can click to expand
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return { icon: 'fas fa-check-circle', color: 'text-green-500' };
      case 'in_progress':
        return { icon: 'fas fa-spinner fa-spin', color: 'text-blue-500' };
      case 'pending':
        return { icon: 'fas fa-clock', color: 'text-gray-400' };
      default:
        return { icon: 'fas fa-exclamation-circle', color: 'text-red-500' };
    }
  };

  const statusIcon = getStatusIcon(stage.status);
  const hasDetails = stage.details && Object.keys(stage.details).length > 0;
  const showDropdown = hasDetails || isResearchPlanningStage || isInformationGatheringStage || isQualityEvaluationStage || isContentSummarizationStage || isReportAssemblyStage;

  return (
    <div className="bg-white border rounded-lg overflow-hidden">
      {/* Main Stage Row */}
      <div 
        className={`flex items-center justify-between p-3 cursor-pointer transition-colors ${
          showDropdown ? 'hover:bg-gray-50' : ''
        }`}
        onClick={() => showDropdown && setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-3">
          <i className={`${statusIcon.icon} ${statusIcon.color}`}></i>
          <span className="text-sm font-medium text-gray-800">{stage.name}</span>
          {showDropdown && (
            <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'} text-xs text-gray-400 transition-transform`}></i>
          )}
        </div>
        <div className="flex items-center space-x-2 text-xs text-gray-500">
          {stage.details?.tokens_used > 0 && (
            <span className="bg-green-100 text-green-700 px-2 py-1 rounded">
              {stage.details.tokens_used} tokens
            </span>
          )}
          {stage.details?.duration > 0 && (
            <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">
              {stage.details.duration.toFixed(1)}s
            </span>
          )}
          {stage.details?.api_calls > 0 && (
            <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded">
              {stage.details.api_calls} calls
            </span>
          )}
        </div>
      </div>

      {/* Dropdown Details */}
      {isExpanded && showDropdown && (
        <div className="border-t bg-gray-50 p-3">
          {/* Research Planning - Special Content */}
          {isResearchPlanningStage ? (
            <div className="space-y-4">
              {/* Standard Stage Details for Research Planning */}
              {hasDetails && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                    <i className="fas fa-cogs text-blue-500 mr-2"></i>
                    Stage Performance Details
                  </h4>
                  <div className="space-y-3">
                    {/* Primary Details Row */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      {stage.details.current_operation && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Current Operation</div>
                          <div className="text-gray-800">{stage.details.current_operation}</div>
                        </div>
                      )}

                      {stage.details.agent && stage.details.agent !== 'Unknown' && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Agent</div>
                          <div className="text-gray-800 flex items-center">
                            <i className="fas fa-robot mr-1 text-blue-500"></i>
                            {stage.details.agent.replace('Agent', '')}
                          </div>
                        </div>
                      )}
                      {stage.details.timestamp && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Last Updated</div>
                          <div className="text-gray-800">
                            {new Date(stage.details.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Performance Metrics Row */}
                    {(stage.details.tokens_used > 0 || stage.details.api_calls > 0 || stage.details.duration > 0 || stage.details.cost_so_far > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Performance Metrics</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {stage.details.tokens_used > 0 && (
                            <div className="bg-green-50 p-2 rounded border border-green-100">
                              <div className="text-xs font-medium text-green-700">{stage.details.tokens_used.toLocaleString()}</div>
                              <div className="text-xs text-green-600">Tokens</div>
                            </div>
                          )}
                          {stage.details.api_calls > 0 && (
                            <div className="bg-purple-50 p-2 rounded border border-purple-100">
                              <div className="text-xs font-medium text-purple-700">{stage.details.api_calls}</div>
                              <div className="text-xs text-purple-600">API Calls</div>
                            </div>
                          )}
                          {stage.details.duration > 0 && (
                            <div className="bg-blue-50 p-2 rounded border border-blue-100">
                              <div className="text-xs font-medium text-blue-700">{stage.details.duration.toFixed(1)}s</div>
                              <div className="text-xs text-blue-600">Duration</div>
                            </div>
                          )}
                          {stage.details.cost_so_far > 0 && (
                            <div className="bg-yellow-50 p-2 rounded border border-yellow-100">
                              <div className="text-xs font-medium text-yellow-700">${stage.details.cost_so_far.toFixed(4)}</div>
                              <div className="text-xs text-yellow-600">Cost</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Additional Details Row */}
                    {(stage.details.model_used || stage.details.sources_found > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Additional Details</div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          {stage.details.model_used && (
                            <div>
                              <div className="font-medium text-gray-600 mb-1">Model Used</div>
                              <div className="text-gray-800 font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                {stage.details.model_used.replace('accounts/fireworks/models/', '')}
                              </div>
                            </div>
                          )}
                          {stage.details.sources_found > 0 && (
                            <div>
                              <div className="font-medium text-gray-600 mb-1">Sources Found</div>
                              <div className="text-gray-800 flex items-center">
                                <i className="fas fa-link mr-1 text-gray-500"></i>
                                {stage.details.sources_found} sources
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Research Plan Analysis Content */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <i className="fas fa-brain text-indigo-500 mr-2"></i>
                  AI Research Plan Analysis
                </h4>
                
                {/* Research Query Display */}
                <div className="bg-gray-50 rounded-lg p-3 mb-3">
                  <div className="text-sm text-gray-600 mb-1">Research Query:</div>
                  <div className="text-sm font-medium text-gray-800 italic">
                    "{progress?.research_plan?.main_query || 'Loading...'}"
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
            </div>
          ) : isInformationGatheringStage ? (
            /* Information Gathering - Special Content */
            <div className="space-y-4">
              {/* Standard Stage Details for Information Gathering */}
              {hasDetails && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                    <i className="fas fa-cogs text-blue-500 mr-2"></i>
                    Stage Performance Details
                  </h4>
                  <div className="space-y-3">
                    {/* Primary Details Row */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      {stage.details.current_operation && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Current Operation</div>
                          <div className="text-gray-800">{stage.details.current_operation}</div>
                        </div>
                      )}

                      {stage.details.agent && stage.details.agent !== 'Unknown' && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Agent</div>
                          <div className="text-gray-800 flex items-center">
                            <i className="fas fa-robot mr-1 text-blue-500"></i>
                            {stage.details.agent.replace('Agent', '')}
                          </div>
                        </div>
                      )}
                      {stage.details.timestamp && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Last Updated</div>
                          <div className="text-gray-800">
                            {new Date(stage.details.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Performance Metrics Row */}
                    {(stage.details.tokens_used > 0 || stage.details.api_calls > 0 || stage.details.duration > 0 || stage.details.cost_so_far > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Performance Metrics</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {stage.details.tokens_used > 0 && (
                            <div className="bg-green-50 p-2 rounded border border-green-100">
                              <div className="text-xs font-medium text-green-700">{stage.details.tokens_used.toLocaleString()}</div>
                              <div className="text-xs text-green-600">Tokens</div>
                            </div>
                          )}
                          {stage.details.api_calls > 0 && (
                            <div className="bg-purple-50 p-2 rounded border border-purple-100">
                              <div className="text-xs font-medium text-purple-700">{stage.details.api_calls}</div>
                              <div className="text-xs text-purple-600">API Calls</div>
                            </div>
                          )}
                          {stage.details.duration > 0 && (
                            <div className="bg-blue-50 p-2 rounded border border-blue-100">
                              <div className="text-xs font-medium text-blue-700">{stage.details.duration.toFixed(1)}s</div>
                              <div className="text-xs text-blue-600">Duration</div>
                            </div>
                          )}
                          {stage.details.cost_so_far > 0 && (
                            <div className="bg-yellow-50 p-2 rounded border border-yellow-100">
                              <div className="text-xs font-medium text-yellow-700">${stage.details.cost_so_far.toFixed(4)}</div>
                              <div className="text-xs text-yellow-600">Cost</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Additional Details Row */}
                    {(stage.details.model_used || stage.details.sources_found > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Additional Details</div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          {stage.details.model_used && (
                            <div>
                              <div className="font-medium text-gray-600 mb-1">Model Used</div>
                              <div className="text-gray-800 font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                {stage.details.model_used.replace('accounts/fireworks/models/', '')}
                              </div>
                            </div>
                          )}
                          {stage.details.sources_found > 0 && (
                            <div>
                              <div className="font-medium text-gray-600 mb-1">Sources Found</div>
                              <div className="text-gray-800 flex items-center">
                                <i className="fas fa-link mr-1 text-gray-500"></i>
                                {stage.details.sources_found} sources
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Information Gathering Analysis Content */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <i className="fas fa-globe text-emerald-500 mr-2"></i>
                  Information Sources & Content
                </h4>
                
                {/* Gathering Status */}
                <div className="bg-gray-50 rounded-lg p-3 mb-3">
                  <div className="text-sm text-gray-600 mb-1">Current Status:</div>
                  <div className="text-sm font-medium text-gray-800">
                    {stage.details?.current_operation || 'Gathering information from web sources...'}
                  </div>
                </div>
                
                {/* Sources Overview */}
                {(stage.details?.sources_found > 0 || stage.details?.sources) && (
                  <div className="bg-emerald-50 rounded-lg p-3 mb-3 border border-emerald-200">
                    <div className="text-sm font-semibold text-emerald-700 mb-2 flex items-center">
                      <i className="fas fa-chart-bar mr-1"></i>
                      Sources Discovery Summary
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="bg-white rounded-lg p-3">
                        <div className="text-xs font-semibold text-emerald-700 mb-2">
                          <i className="fas fa-link mr-1"></i>
                          Sources Found
                        </div>
                        <div className="text-lg font-bold text-emerald-800">
                          {stage.details?.sources?.length || stage.details?.sources_found || 0}
                        </div>
                        <div className="text-xs text-emerald-600">Unique websites</div>
                      </div>
                      
                      <div className="bg-white rounded-lg p-3">
                        <div className="text-xs font-semibold text-blue-700 mb-2">
                          <i className="fas fa-file-alt mr-1"></i>
                          Content Extracted
                        </div>
                        <div className="text-lg font-bold text-blue-800">
                          {stage.details?.sources?.filter(s => s.snippet && s.snippet.length > 0).length || 0}
                        </div>
                        <div className="text-xs text-blue-600">With content</div>
                      </div>
                      
                      <div className="bg-white rounded-lg p-3">
                        <div className="text-xs font-semibold text-purple-700 mb-2">
                          <i className="fas fa-check-circle mr-1"></i>
                          Status
                        </div>
                        <div className="text-sm font-bold text-purple-800">
                          {stage.status === 'completed' ? 'Complete' : 
                           stage.status === 'in_progress' ? 'In Progress' : 'Pending'}
                        </div>
                        <div className="text-xs text-purple-600">
                          {stage.status === 'completed' ? '✅' : 
                           stage.status === 'in_progress' ? '🔄' : '⏳'}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Debug Sources Data */}
                {console.log(`🔍 Stage ${stage.name} - Sources check:`, {
                  hasDetails: !!stage.details,
                  hasSources: !!(stage.details?.sources),
                  sourcesLength: stage.details?.sources?.length || 0,
                  sourcesData: stage.details?.sources?.slice(0, 2) || 'No sources'
                })}
                
                {/* Enhanced Source Discovery & Filtering Display */}
                {stage.details?.source_filtering ? (
                  <SourceFilteringCard filteringData={stage.details.source_filtering} />
                ) : stage.details?.sources && stage.details.sources.length > 0 ? (
                  <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
                    <div className="text-sm font-semibold text-emerald-700 mb-3 flex items-center">
                      <i className="fas fa-list-ul mr-1"></i>
                      Discovered Sources ({stage.details.sources.length})
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
                      {stage.details.sources.map((source, idx) => (
                        <SourceCard key={idx} source={source} index={idx} />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-600 mx-auto mb-2"></div>
                    <div className="text-sm text-gray-600">Discovering and analyzing web sources...</div>
                    <div className="text-xs text-gray-500">Searching for relevant information across the web</div>
                  </div>
                )}
              </div>
            </div>
          ) : isQualityEvaluationStage ? (
            /* Quality Evaluation - Special Content */
            <div className="space-y-4">
              {/* Standard Stage Details for Quality Evaluation */}
              {hasDetails && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                    <i className="fas fa-cogs text-blue-500 mr-2"></i>
                    Stage Performance Details
                  </h4>
                  <div className="space-y-3">
                    {/* Primary Details Row */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      {stage.details.current_operation && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Current Operation</div>
                          <div className="text-gray-800">{stage.details.current_operation}</div>
                        </div>
                      )}

                      {stage.details.agent && stage.details.agent !== 'Unknown' && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Agent</div>
                          <div className="text-gray-800 flex items-center">
                            <i className="fas fa-robot mr-1 text-blue-500"></i>
                            {stage.details.agent.replace('Agent', '')}
                          </div>
                        </div>
                      )}
                      {stage.details.timestamp && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Last Updated</div>
                          <div className="text-gray-800">
                            {new Date(stage.details.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Performance Metrics Row */}
                    {(stage.details.tokens_used > 0 || stage.details.api_calls > 0 || stage.details.duration > 0 || stage.details.cost_so_far > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Performance Metrics</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {stage.details.tokens_used > 0 && (
                            <div className="bg-green-50 p-2 rounded border border-green-100">
                              <div className="text-xs font-medium text-green-700">{stage.details.tokens_used.toLocaleString()}</div>
                              <div className="text-xs text-green-600">Tokens</div>
                            </div>
                          )}
                          {stage.details.api_calls > 0 && (
                            <div className="bg-purple-50 p-2 rounded border border-purple-100">
                              <div className="text-xs font-medium text-purple-700">{stage.details.api_calls}</div>
                              <div className="text-xs text-purple-600">API Calls</div>
                            </div>
                          )}
                          {stage.details.duration > 0 && (
                            <div className="bg-blue-50 p-2 rounded border border-blue-100">
                              <div className="text-xs font-medium text-blue-700">{stage.details.duration.toFixed(1)}s</div>
                              <div className="text-xs text-blue-600">Duration</div>
                            </div>
                          )}
                          {stage.details.cost_so_far > 0 && (
                            <div className="bg-yellow-50 p-2 rounded border border-yellow-100">
                              <div className="text-xs font-medium text-yellow-700">${stage.details.cost_so_far.toFixed(4)}</div>
                              <div className="text-xs text-yellow-600">Cost</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Additional Details Row */}
                    {(stage.details.model_used || stage.details.sources_found > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Additional Details</div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          {stage.details.model_used && (
                            <div>
                              <div className="font-medium text-gray-600 mb-1">Model Used</div>
                              <div className="text-gray-800 font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                {stage.details.model_used.replace('accounts/fireworks/models/', '')}
                              </div>
                            </div>
                          )}
                          {stage.details.sources_found > 0 && (
                            <div>
                              <div className="font-medium text-gray-600 mb-1">Sources Found</div>
                              <div className="text-gray-800 flex items-center">
                                <i className="fas fa-link mr-1 text-gray-500"></i>
                                {stage.details.sources_found} sources
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Quality Evaluation Analysis Content */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <i className="fas fa-microscope text-amber-500 mr-2"></i>
                  AI Quality Assessment Results
                </h4>
                
                {/* Evaluation Status */}
                <div className="bg-gray-50 rounded-lg p-3 mb-3">
                  <div className="text-sm text-gray-600 mb-1">Current Status:</div>
                  <div className="text-sm font-medium text-gray-800">
                    {stage.details?.current_operation || 'Evaluating information quality and relevance...'}
                  </div>
                </div>
                
                {/* Debug Quality Evaluations Data */}
                {console.log(`🔍 Quality Evaluation Debug:`, {
                  stageName: stage.name,
                  hasDetails: !!stage.details,
                  hasQualityEvaluations: !!(stage.details?.quality_evaluations),
                  qualityEvaluationsLength: stage.details?.quality_evaluations?.length || 0,
                  qualityEvaluationsData: stage.details?.quality_evaluations?.slice(0, 1) || 'No evaluations',
                  allStageDetails: stage.details
                })}
                
                {/* Quality Evaluations */}
                {stage.details?.quality_evaluations && stage.details.quality_evaluations.length > 0 ? (
                  <div className="space-y-4">
                    {/* Overall Quality Summary */}
                    <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                      <div className="text-sm font-semibold text-amber-700 mb-2 flex items-center">
                        <i className="fas fa-chart-line mr-1"></i>
                        Quality Assessment Summary
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-amber-700 mb-2">
                            <i className="fas fa-clipboard-check mr-1"></i>
                            Evaluations
                          </div>
                          <div className="text-lg font-bold text-amber-800">
                            {stage.details.quality_evaluations.length}
                          </div>
                          <div className="text-xs text-amber-600">Sub-questions</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-green-700 mb-2">
                            <i className="fas fa-check-circle mr-1"></i>
                            Passed
                          </div>
                          <div className="text-lg font-bold text-green-800">
                            {stage.details.quality_evaluations.filter(e => e.pass_fail_status === 'PASS').length}
                          </div>
                          <div className="text-xs text-green-600">Quality checks</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-red-700 mb-2">
                            <i className="fas fa-times-circle mr-1"></i>
                            Failed
                          </div>
                          <div className="text-lg font-bold text-red-800">
                            {stage.details.quality_evaluations.filter(e => e.pass_fail_status === 'FAIL').length}
                          </div>
                          <div className="text-xs text-red-600">Quality checks</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-blue-700 mb-2">
                            <i className="fas fa-star mr-1"></i>
                            Avg Grade
                          </div>
                          <div className="text-lg font-bold text-blue-800">
                            {stage.details.quality_evaluations.length > 0 
                              ? Math.round((stage.details.quality_evaluations.reduce((sum, e) => sum + e.overall_confidence, 0) / stage.details.quality_evaluations.length) * 100) + '%'
                              : 'N/A'
                            }
                          </div>
                          <div className="text-xs text-blue-600">Confidence</div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Individual Quality Evaluations */}
                    <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                      <div className="text-sm font-semibold text-amber-700 mb-3 flex items-center">
                        <i className="fas fa-list-ul mr-1"></i>
                        Detailed Quality Assessment Results
                      </div>
                      <div className="space-y-4 max-h-96 overflow-y-auto scrollbar-thin">
                        {stage.details.quality_evaluations.map((evaluation, idx) => (
                          <QualityEvaluationCard key={idx} evaluation={evaluation} index={idx} />
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-amber-600 mx-auto mb-2"></div>
                    <div className="text-sm text-gray-600">Running quality assessment...</div>
                    <div className="text-xs text-gray-500">AI is evaluating source quality and relevance</div>
                  </div>
                )}
              </div>
            </div>
          ) : isContentSummarizationStage ? (
            /* Content Summarization - Special Content */
            <div className="space-y-4">
              {/* Standard Stage Details for Content Summarization */}
              {hasDetails && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                    <i className="fas fa-cogs text-blue-500 mr-2"></i>
                    Stage Performance Details
                  </h4>
                  <div className="space-y-3">
                    {/* Primary Details Row */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      {stage.details.current_operation && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Current Operation</div>
                          <div className="text-gray-800">{stage.details.current_operation}</div>
                        </div>
                      )}

                      {stage.details.agent && stage.details.agent !== 'Unknown' && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Agent</div>
                          <div className="text-gray-800 flex items-center">
                            <i className="fas fa-robot mr-1 text-blue-500"></i>
                            {stage.details.agent.replace('Agent', '')}
                          </div>
                        </div>
                      )}
                      {stage.details.timestamp && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Last Updated</div>
                          <div className="text-gray-800">
                            {new Date(stage.details.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Performance Metrics Row */}
                    {(stage.details.tokens_used > 0 || stage.details.api_calls > 0 || stage.details.duration > 0 || stage.details.cost_so_far > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Performance Metrics</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {stage.details.tokens_used > 0 && (
                            <div className="bg-green-50 p-2 rounded border border-green-100">
                              <div className="text-xs font-medium text-green-700">{stage.details.tokens_used.toLocaleString()}</div>
                              <div className="text-xs text-green-600">Tokens</div>
                            </div>
                          )}
                          {stage.details.api_calls > 0 && (
                            <div className="bg-purple-50 p-2 rounded border border-purple-100">
                              <div className="text-xs font-medium text-purple-700">{stage.details.api_calls}</div>
                              <div className="text-xs text-purple-600">API Calls</div>
                            </div>
                          )}
                          {stage.details.duration > 0 && (
                            <div className="bg-blue-50 p-2 rounded border border-blue-100">
                              <div className="text-xs font-medium text-blue-700">{stage.details.duration.toFixed(1)}s</div>
                              <div className="text-xs text-blue-600">Duration</div>
                            </div>
                          )}
                          {stage.details.cost_so_far > 0 && (
                            <div className="bg-yellow-50 p-2 rounded border border-yellow-100">
                              <div className="text-xs font-medium text-yellow-700">${stage.details.cost_so_far.toFixed(4)}</div>
                              <div className="text-xs text-yellow-600">Cost</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Additional Details Row */}
                    {(stage.details.model_used || stage.details.sources_found > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Additional Details</div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          {stage.details.model_used && (
                            <div>
                              <div className="font-medium text-gray-600 mb-1">Model Used</div>
                              <div className="text-gray-800 font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                {stage.details.model_used.replace('accounts/fireworks/models/', '')}
                              </div>
                            </div>
                          )}
                          {stage.details.sources_found > 0 && (
                            <div>
                              <div className="font-medium text-gray-600 mb-1">Sources Found</div>
                              <div className="text-gray-800 flex items-center">
                                <i className="fas fa-link mr-1 text-gray-500"></i>
                                {stage.details.sources_found} sources
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Content Summarization Analysis Content */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <i className="fas fa-magic text-indigo-500 mr-2"></i>
                  AI Content Summarization Results
                </h4>
                
                {/* Summarization Status */}
                <div className="bg-gray-50 rounded-lg p-3 mb-3">
                  <div className="text-sm text-gray-600 mb-1">Current Status:</div>
                  <div className="text-sm font-medium text-gray-800">
                    {stage.details?.current_operation || 'Analyzing and summarizing content...'}
                  </div>
                </div>
                
                {/* Debug Summaries Data */}
                {console.log(`🔍 Content Summarization Debug:`, {
                  stageName: stage.name,
                  hasDetails: !!stage.details,
                  hasSummaries: !!(stage.details?.summaries || progress?.summaries),
                  summariesLength: (stage.details?.summaries || progress?.summaries || []).length,
                  summariesData: (stage.details?.summaries || progress?.summaries || []).slice(0, 1),
                  progressData: progress,
                  allStageDetails: stage.details
                })}
                
                {/* Research Summaries */}
                {(stage.details?.summaries || progress?.summaries) && (stage.details?.summaries || progress?.summaries).length > 0 ? (
                  <div className="space-y-4">
                    {/* Overall Summary Statistics */}
                    <div className="bg-indigo-50 rounded-lg p-3 border border-indigo-200">
                      <div className="text-sm font-semibold text-indigo-700 mb-2 flex items-center">
                        <i className="fas fa-chart-bar mr-1"></i>
                        Summarization Overview
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-indigo-700 mb-2">
                            <i className="fas fa-file-alt mr-1"></i>
                            Summaries
                          </div>
                          <div className="text-lg font-bold text-indigo-800">
                            {(stage.details?.summaries || progress?.summaries || []).length}
                          </div>
                          <div className="text-xs text-indigo-600">Generated</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-green-700 mb-2">
                            <i className="fas fa-check-circle mr-1"></i>
                            High Confidence
                          </div>
                          <div className="text-lg font-bold text-green-800">
                            {(stage.details?.summaries || progress?.summaries || []).filter(s => s.confidence_level >= 0.8).length}
                          </div>
                          <div className="text-xs text-green-600">≥80% confidence</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-blue-700 mb-2">
                            <i className="fas fa-brain mr-1"></i>
                            Avg Confidence
                          </div>
                          <div className="text-lg font-bold text-blue-800">
                            {(stage.details?.summaries || progress?.summaries || []).length > 0 
                              ? Math.round((stage.details?.summaries || progress?.summaries || []).reduce((sum, s) => sum + (s.confidence_level || 0), 0) / (stage.details?.summaries || progress?.summaries || []).length * 100) + '%'
                              : 'N/A'
                            }
                          </div>
                          <div className="text-xs text-blue-600">Overall</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-purple-700 mb-2">
                            <i className="fas fa-file-word mr-1"></i>
                            Total Words
                          </div>
                          <div className="text-lg font-bold text-purple-800">
                            {(stage.details?.summaries || progress?.summaries || []).reduce((sum, s) => sum + (s.word_count || 0), 0).toLocaleString()}
                          </div>
                          <div className="text-xs text-purple-600">Generated</div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Individual Summaries */}
                    <div className="bg-indigo-50 rounded-lg p-3 border border-indigo-200">
                      <div className="text-sm font-semibold text-indigo-700 mb-3 flex items-center">
                        <i className="fas fa-list-ul mr-1"></i>
                        Research Question Summaries
                      </div>
                      <div className="space-y-4 max-h-96 overflow-y-auto scrollbar-thin">
                        {(stage.details?.summaries || progress?.summaries || []).map((summary, idx) => (
                          <div key={idx} className="bg-white rounded-lg p-4 border border-indigo-100 shadow-sm">
                            {/* Summary Header */}
                            <div className="flex items-start justify-between mb-3">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <div className="flex items-center justify-center w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full text-xs font-bold">
                                    {summary.sub_question_id || idx + 1}
                                  </div>
                                  <div className="text-sm font-medium text-gray-800">
                                    {summary.question}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 text-xs">
                                  <span className={`px-2 py-1 rounded-full font-medium ${
                                    (summary.confidence_level || 0) >= 0.8 ? 'bg-green-100 text-green-700' :
                                    (summary.confidence_level || 0) >= 0.6 ? 'bg-yellow-100 text-yellow-700' :
                                    'bg-red-100 text-red-700'
                                  }`}>
                                    {Math.round((summary.confidence_level || 0) * 100)}% confidence
                                  </span>
                                  {summary.word_count && (
                                    <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded-full font-medium">
                                      {summary.word_count} words
                                    </span>
                                  )}
                                  {summary.processing_time && (
                                    <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-medium">
                                      {summary.processing_time.toFixed(1)}s
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            {/* Summary Answer */}
                            <div className="mb-3">
                              <div className="text-xs font-medium text-gray-700 mb-2">
                                <i className="fas fa-lightbulb mr-1 text-indigo-500"></i>
                                AI Generated Answer:
                              </div>
                              <div className="text-sm text-gray-800 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-3 border border-indigo-100">
                                {summary.answer}
                              </div>
                            </div>
                            
                            {/* Key Points */}
                            {summary.key_points && summary.key_points.length > 0 && (
                              <div className="mb-3">
                                <div className="text-xs font-medium text-gray-700 mb-2">
                                  <i className="fas fa-list-ul mr-1 text-indigo-500"></i>
                                  Key Points ({summary.key_points.length}):
                                </div>
                                <div className="space-y-2">
                                  {summary.key_points.map((point, pointIdx) => (
                                    <div key={pointIdx} className="text-sm text-gray-700 bg-white rounded-lg p-2 border border-gray-200 flex items-start">
                                      <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full mr-2 mt-1.5 flex-shrink-0"></div>
                                      <div>{point}</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Sources Used */}
                            {summary.sources && summary.sources.length > 0 && (
                              <div className="mb-3">
                                <div className="text-xs font-medium text-gray-700 mb-2">
                                  <i className="fas fa-link mr-1 text-indigo-500"></i>
                                  Sources Used ({summary.sources.length}):
                                </div>
                                <div className="flex flex-wrap gap-1">
                                  {summary.sources.map((source, sourceIdx) => (
                                    <a 
                                      key={sourceIdx}
                                      href={source}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded hover:bg-blue-100 transition-colors"
                                    >
                                      Source {sourceIdx + 1}
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Summary Actions */}
                            <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                              <button 
                                onClick={() => {
                                  const summaryText = `Question: ${summary.question}\n\nAnswer: ${summary.answer}\n\nKey Points:\n${(summary.key_points || []).map(p => `• ${p}`).join('\n')}`;
                                  navigator.clipboard.writeText(summaryText);
                                }}
                                className="text-xs text-gray-600 hover:text-gray-800 flex items-center gap-1"
                              >
                                <i className="fas fa-copy"></i>
                                <span>Copy Summary</span>
                              </button>
                              <button 
                                onClick={() => {
                                  navigator.clipboard.writeText(summary.answer);
                                }}
                                className="text-xs text-gray-600 hover:text-gray-800 flex items-center gap-1"
                              >
                                <i className="fas fa-quote-left"></i>
                                <span>Copy Answer</span>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto mb-2"></div>
                    <div className="text-sm text-gray-600">Generating content summaries...</div>
                    <div className="text-xs text-gray-500">AI is analyzing and summarizing research findings</div>
                  </div>
                )}
              </div>
            </div>
          ) : isReportAssemblyStage ? (
            /* Report Assembly - Special Content */
            <div className="space-y-4">
              {/* Standard Stage Details for Report Assembly */}
              {hasDetails && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                    <i className="fas fa-cogs text-blue-500 mr-2"></i>
                    Stage Performance Details
                  </h4>
                  <div className="space-y-3">
                    {/* Primary Details Row */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      {stage.details.current_operation && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Current Operation</div>
                          <div className="text-gray-800">{stage.details.current_operation}</div>
                        </div>
                      )}

                      {stage.details.agent && stage.details.agent !== 'Unknown' && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Agent</div>
                          <div className="text-gray-800 flex items-center">
                            <i className="fas fa-robot mr-1 text-blue-500"></i>
                            {stage.details.agent.replace('Agent', '')}
                          </div>
                        </div>
                      )}
                      {stage.details.timestamp && (
                        <div>
                          <div className="font-medium text-gray-600 mb-1">Last Updated</div>
                          <div className="text-gray-800">
                            {new Date(stage.details.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Performance Metrics Row */}
                    {(stage.details.tokens_used > 0 || stage.details.api_calls > 0 || stage.details.duration > 0 || stage.details.cost_so_far > 0) && (
                      <div className="border-t pt-3">
                        <div className="font-medium text-gray-600 mb-2 text-xs">Performance Metrics</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {stage.details.tokens_used > 0 && (
                            <div className="bg-green-50 p-2 rounded border border-green-100">
                              <div className="text-xs font-medium text-green-700">{stage.details.tokens_used.toLocaleString()}</div>
                              <div className="text-xs text-green-600">Tokens</div>
                            </div>
                          )}
                          {stage.details.api_calls > 0 && (
                            <div className="bg-purple-50 p-2 rounded border border-purple-100">
                              <div className="text-xs font-medium text-purple-700">{stage.details.api_calls}</div>
                              <div className="text-xs text-purple-600">API Calls</div>
                            </div>
                          )}
                          {stage.details.duration > 0 && (
                            <div className="bg-blue-50 p-2 rounded border border-blue-100">
                              <div className="text-xs font-medium text-blue-700">{stage.details.duration.toFixed(1)}s</div>
                              <div className="text-xs text-blue-600">Duration</div>
                            </div>
                          )}
                          {stage.details.cost_so_far > 0 && (
                            <div className="bg-yellow-50 p-2 rounded border border-yellow-100">
                              <div className="text-xs font-medium text-yellow-700">${stage.details.cost_so_far.toFixed(4)}</div>
                              <div className="text-xs text-yellow-600">Cost</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Final Report Content */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <i className="fas fa-file-alt text-emerald-500 mr-2"></i>
                  Final Research Report
                </h4>
                
                {/* Report Status */}
                <div className="bg-gray-50 rounded-lg p-3 mb-3">
                  <div className="text-sm text-gray-600 mb-1">Assembly Status:</div>
                  <div className="text-sm font-medium text-gray-800">
                    {stage.details?.current_operation || 'Assembling final research report...'}
                  </div>
                </div>
                
                {/* Debug Final Report Data */}
                {console.log(`📋 Report Assembly Debug:`, {
                  stageName: stage.name,
                  hasDetails: !!stage.details,
                  hasFinalReport: !!(stage.details?.final_report),
                  finalReportData: stage.details?.final_report,
                  allStageDetails: stage.details
                })}
                
                {/* Final Report Content */}
                {stage.details?.final_report ? (
                  <div className="space-y-4">
                    {/* Report Overview Statistics */}
                    <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
                      <div className="text-sm font-semibold text-emerald-700 mb-2 flex items-center">
                        <i className="fas fa-chart-line mr-1"></i>
                        Report Overview
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-emerald-700 mb-2">
                            <i className="fas fa-list-alt mr-1"></i>
                            Findings
                          </div>
                          <div className="text-lg font-bold text-emerald-800">
                            {(stage.details.final_report.detailed_findings || []).length}
                          </div>
                          <div className="text-xs text-emerald-600">Sections</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-blue-700 mb-2">
                            <i className="fas fa-star mr-1"></i>
                            Quality Score
                          </div>
                          <div className="text-lg font-bold text-blue-800">
                            {stage.details.final_report.quality_score 
                              ? Math.round(stage.details.final_report.quality_score * 100) + '%'
                              : 'N/A'
                            }
                          </div>
                          <div className="text-xs text-blue-600">Overall</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-purple-700 mb-2">
                            <i className="fas fa-link mr-1"></i>
                            Sources
                          </div>
                          <div className="text-lg font-bold text-purple-800">
                            {(stage.details.final_report.sources_cited || []).length}
                          </div>
                          <div className="text-xs text-purple-600">Referenced</div>
                        </div>
                        
                        <div className="bg-white rounded-lg p-3">
                          <div className="text-xs font-semibold text-amber-700 mb-2">
                            <i className="fas fa-file-word mr-1"></i>
                            Word Count
                          </div>
                          <div className="text-lg font-bold text-amber-800">
                            {(stage.details.final_report.total_words || 0).toLocaleString()}
                          </div>
                          <div className="text-xs text-amber-600">Generated</div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Executive Summary */}
                    {/* Debug logging */}
                    {console.log('🔍 Final Report Data:', stage.details.final_report) || ''}
                    {console.log('📋 Executive Summary Value:', stage.details.final_report.executive_summary) || ''}
                    {console.log('📋 Executive Summary Type:', typeof stage.details.final_report.executive_summary) || ''}
                    {console.log('📋 Executive Summary Length:', stage.details.final_report.executive_summary?.length) || ''}
                    
                    {(stage.details.final_report.executive_summary && stage.details.final_report.executive_summary.trim()) && (
                      <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
                        <div className="text-sm font-semibold text-emerald-700 mb-3 flex items-center">
                          <i className="fas fa-scroll mr-1"></i>
                          Executive Summary
                        </div>
                        <div className="text-sm text-gray-800 bg-white rounded-lg p-3 border border-emerald-100 leading-relaxed">
                          {stage.details.final_report.executive_summary}
                        </div>
                      </div>
                    )}
                    
                    {/* Detailed Findings from Content Summarization */}
                    {stage.details.final_report.detailed_findings && stage.details.final_report.detailed_findings.length > 0 && (
                      <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
                        <div className="text-sm font-semibold text-emerald-700 mb-3 flex items-center">
                          <i className="fas fa-list-ol mr-1"></i>
                          Detailed Research Findings
                        </div>
                        <div className="space-y-3 max-h-96 overflow-y-auto scrollbar-thin">
                          {stage.details.final_report.detailed_findings.map((finding, idx) => (
                            <div key={idx} className="bg-white rounded-lg p-4 border border-emerald-100 shadow-sm">
                              <div className="flex items-start justify-between mb-2">
                                <div className="flex items-center gap-2 mb-2">
                                  <div className="flex items-center justify-center w-6 h-6 bg-emerald-100 text-emerald-600 rounded-full text-xs font-bold">
                                    {idx + 1}
                                  </div>
                                  <div className="text-sm font-medium text-gray-800">
                                    {finding.question}
                                  </div>
                                </div>
                                {finding.confidence_level && (
                                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                    finding.confidence_level >= 0.8 ? 'bg-green-100 text-green-700' :
                                    finding.confidence_level >= 0.6 ? 'bg-yellow-100 text-yellow-700' :
                                    'bg-red-100 text-red-700'
                                  }`}>
                                    {Math.round(finding.confidence_level * 100)}% confidence
                                  </span>
                                )}
                              </div>
                              
                              <div className="text-sm text-gray-800 bg-gradient-to-r from-emerald-50 to-green-50 rounded-lg p-3 border border-emerald-100 mb-3">
                                {finding.answer}
                              </div>
                              
                              {finding.key_points && finding.key_points.length > 0 && (
                                <div className="space-y-1">
                                  <div className="text-xs font-medium text-gray-700 mb-2">
                                    <i className="fas fa-key mr-1 text-emerald-500"></i>
                                    Key Points:
                                  </div>
                                  {finding.key_points.map((point, pointIdx) => (
                                    <div key={pointIdx} className="text-sm text-gray-700 bg-gray-50 rounded-lg p-2 border border-gray-200 flex items-start">
                                      <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-2 mt-1.5 flex-shrink-0"></div>
                                      <div>{point}</div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Recommendations */}
                    {stage.details.final_report.recommendations && stage.details.final_report.recommendations.length > 0 && (
                      <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
                        <div className="text-sm font-semibold text-emerald-700 mb-3 flex items-center">
                          <i className="fas fa-lightbulb mr-1"></i>
                          Recommendations ({stage.details.final_report.recommendations.length})
                        </div>
                        <div className="space-y-2">
                          {stage.details.final_report.recommendations.map((recommendation, idx) => (
                            <div key={idx} className="text-sm text-gray-800 bg-white rounded-lg p-3 border border-emerald-100 flex items-start">
                              <div className="flex items-center justify-center w-5 h-5 bg-emerald-100 text-emerald-600 rounded-full text-xs font-bold mr-3 flex-shrink-0 mt-0.5">
                                {idx + 1}
                              </div>
                              <div>{recommendation}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Methodology & Limitations */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {stage.details.final_report.methodology && (
                        <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
                          <div className="text-sm font-semibold text-emerald-700 mb-2 flex items-center">
                            <i className="fas fa-cogs mr-1"></i>
                            Methodology
                          </div>
                          <div className="text-sm text-gray-800 bg-white rounded-lg p-3 border border-emerald-100">
                            {stage.details.final_report.methodology}
                          </div>
                        </div>
                      )}
                      
                      {stage.details.final_report.limitations && stage.details.final_report.limitations.length > 0 && (
                        <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                          <div className="text-sm font-semibold text-amber-700 mb-2 flex items-center">
                            <i className="fas fa-exclamation-triangle mr-1"></i>
                            Limitations ({stage.details.final_report.limitations.length})
                          </div>
                          <div className="space-y-1">
                            {stage.details.final_report.limitations.map((limitation, idx) => (
                              <div key={idx} className="text-sm text-gray-800 bg-white rounded-lg p-2 border border-amber-100 flex items-start">
                                <div className="w-1.5 h-1.5 bg-amber-500 rounded-full mr-2 mt-1.5 flex-shrink-0"></div>
                                <div>{limitation}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Report Actions */}
                    <div className="flex items-center gap-2 pt-3 border-t border-gray-200">
                      <button 
                        onClick={() => {
                          const reportText = `${stage.details.final_report.executive_summary}\n\nDetailed Findings:\n${(stage.details.final_report.detailed_findings || []).map((f, i) => `${i+1}. ${f.question}\n${f.answer}\n`).join('\n')}\n\nRecommendations:\n${(stage.details.final_report.recommendations || []).map((r, i) => `${i+1}. ${r}`).join('\n')}`;
                          navigator.clipboard.writeText(reportText);
                        }}
                        className="text-xs text-gray-600 hover:text-gray-800 flex items-center gap-1"
                      >
                        <i className="fas fa-copy"></i>
                        <span>Copy Full Report</span>
                      </button>
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(stage.details.final_report.executive_summary);
                        }}
                        className="text-xs text-gray-600 hover:text-gray-800 flex items-center gap-1"
                      >
                        <i className="fas fa-scroll"></i>
                        <span>Copy Executive Summary</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-600 mx-auto mb-2"></div>
                    <div className="text-sm text-gray-600">Assembling final research report...</div>
                    <div className="text-xs text-gray-500">Synthesizing all research findings into comprehensive report</div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Standard Stage Details for Other Stages */
            <div className="space-y-4">
              {/* Primary Details Row */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
              {stage.details.current_operation && (
                <div>
                  <div className="font-medium text-gray-600 mb-1">Current Operation</div>
                  <div className="text-gray-800">{stage.details.current_operation}</div>
                </div>
              )}

              {stage.details.agent && stage.details.agent !== 'Unknown' && (
                <div>
                  <div className="font-medium text-gray-600 mb-1">Agent</div>
                  <div className="text-gray-800 flex items-center">
                    <i className="fas fa-robot mr-1 text-blue-500"></i>
                    {stage.details.agent.replace('Agent', '')}
                  </div>
                </div>
              )}
              {stage.details.timestamp && (
                <div>
                  <div className="font-medium text-gray-600 mb-1">Last Updated</div>
                  <div className="text-gray-800">
                    {new Date(stage.details.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              )}
            </div>

            {/* Performance Metrics Row */}
            {(stage.details.tokens_used > 0 || stage.details.api_calls > 0 || stage.details.duration > 0 || stage.details.cost_so_far > 0) && (
              <div className="border-t pt-3">
                <div className="font-medium text-gray-600 mb-2 text-xs">Performance Metrics</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {stage.details.tokens_used > 0 && (
                    <div className="bg-green-50 p-2 rounded border border-green-100">
                      <div className="text-xs font-medium text-green-700">{stage.details.tokens_used.toLocaleString()}</div>
                      <div className="text-xs text-green-600">Tokens</div>
                    </div>
                  )}
                  {stage.details.api_calls > 0 && (
                    <div className="bg-purple-50 p-2 rounded border border-purple-100">
                      <div className="text-xs font-medium text-purple-700">{stage.details.api_calls}</div>
                      <div className="text-xs text-purple-600">API Calls</div>
                    </div>
                  )}
                  {stage.details.duration > 0 && (
                    <div className="bg-blue-50 p-2 rounded border border-blue-100">
                      <div className="text-xs font-medium text-blue-700">{stage.details.duration.toFixed(1)}s</div>
                      <div className="text-xs text-blue-600">Duration</div>
                    </div>
                  )}
                  {stage.details.cost_so_far > 0 && (
                    <div className="bg-yellow-50 p-2 rounded border border-yellow-100">
                      <div className="text-xs font-medium text-yellow-700">${stage.details.cost_so_far.toFixed(4)}</div>
                      <div className="text-xs text-yellow-600">Cost</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Additional Details Row */}
            {(stage.details.model_used || stage.details.sources_found > 0) && (
              <div className="border-t pt-3">
                <div className="font-medium text-gray-600 mb-2 text-xs">Additional Details</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {stage.details.model_used && (
                    <div>
                      <div className="font-medium text-gray-600 mb-1">Model Used</div>
                      <div className="text-gray-800 font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                        {stage.details.model_used.replace('accounts/fireworks/models/', '')}
                      </div>
                    </div>
                  )}
                  {stage.details.sources_found > 0 && (
                    <div>
                      <div className="font-medium text-gray-600 mb-1">Sources Found</div>
                      <div className="text-gray-800 flex items-center">
                        <i className="fas fa-link mr-1 text-gray-500"></i>
                        {stage.details.sources_found} sources
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Enhanced Source Filtering Card Component for showing accepted and rejected sources
const SourceFilteringCard = ({ filteringData }) => {
  const [activeTab, setActiveTab] = useState('accepted');
  const [isDetailsExpanded, setIsDetailsExpanded] = useState(false);
  
  if (!filteringData) {
    return (
      <div className="bg-gray-50 rounded-lg p-4 text-center">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-600 mx-auto mb-2"></div>
        <div className="text-sm text-gray-600">Discovering and analyzing web sources...</div>
        <div className="text-xs text-gray-500">Searching for relevant information across the web</div>
      </div>
    );
  }

  const { accepted_sources = [], rejected_sources = [], filtering_summary = {} } = filteringData;
  
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header with Filtering Summary */}
      <div className="bg-gradient-to-r from-emerald-50 to-blue-50 p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-800 flex items-center">
              <i className="fas fa-filter mr-2 text-emerald-600"></i>
              Source Discovery & Quality Filtering
            </h3>
            <p className="text-xs text-gray-600 mt-1">
              AI-powered filtering applied: <span className="font-medium">{filtering_summary.strategy || 'Smart'}</span> strategy
            </p>
          </div>
          <button
            onClick={() => setIsDetailsExpanded(!isDetailsExpanded)}
            className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors"
          >
            <i className={`fas fa-chevron-${isDetailsExpanded ? 'up' : 'down'}`}></i>
            Details
          </button>
        </div>
        
        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-3 mt-3">
          <div className="bg-white rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-gray-700">{filtering_summary.original_count || 0}</div>
            <div className="text-xs text-gray-500">Found</div>
          </div>
          <div className="bg-white rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-emerald-600">{accepted_sources.length}</div>
            <div className="text-xs text-emerald-700">Accepted</div>
          </div>
          <div className="bg-white rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-red-500">{rejected_sources.length}</div>
            <div className="text-xs text-red-600">Filtered Out</div>
          </div>
          <div className="bg-white rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-blue-600">
              {filtering_summary.original_count > 0 
                ? Math.round((rejected_sources.length / filtering_summary.original_count) * 100) + '%'
                : '0%'
              }
            </div>
            <div className="text-xs text-blue-700">Filter Rate</div>
          </div>
        </div>

        {/* Filtering Details (Expandable) */}
        {isDetailsExpanded && (
          <div className="mt-4 p-3 bg-white rounded-lg border border-gray-100">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div>
                <div className="font-medium text-gray-700 mb-2">Filtering Strategy</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>Strategy:</span>
                    <span className="font-medium capitalize">{filtering_summary.strategy || 'Smart'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Topic Type:</span>
                    <span className="font-medium capitalize">{filtering_summary.topic_classification || 'General'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Confidence Boost:</span>
                    <span className="font-medium text-emerald-600">+{((filtering_summary.confidence_boost || 0) * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
              <div>
                <div className="font-medium text-gray-700 mb-2">Quality Thresholds</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>Authority:</span>
                    <span className="font-medium">{((filtering_summary.thresholds?.authority || 0.3) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Relevance:</span>
                    <span className="font-medium">{((filtering_summary.thresholds?.relevance || 0.3) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Content Quality:</span>
                    <span className="font-medium">{((filtering_summary.thresholds?.content_quality || 0.2) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
              <div>
                <div className="font-medium text-gray-700 mb-2">Quality Analysis</div>
                <div className="space-y-1">
                  {filtering_summary.quality_distribution ? (
                    <>
                      <div className="flex justify-between">
                        <span>Avg Authority:</span>
                        <span className="font-medium">{((filtering_summary.quality_distribution.mean_authority || 0.5) * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Avg Relevance:</span>
                        <span className="font-medium">{((filtering_summary.quality_distribution.mean_relevance || 0.5) * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Avg Quality:</span>
                        <span className="font-medium">{((filtering_summary.quality_distribution.mean_quality || 0.5) * 100).toFixed(0)}%</span>
                      </div>
                    </>
                  ) : (
                    <div className="text-gray-500 text-xs italic">Computing quality metrics...</div>
                  )}
                </div>
              </div>
            </div>
            {filtering_summary.reasoning && filtering_summary.reasoning.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="font-medium text-gray-700 mb-2 text-xs">Filtering Reasoning:</div>
                <div className="space-y-1">
                  {filtering_summary.reasoning.slice(0, 3).map((reason, idx) => (
                    <div key={idx} className="text-xs text-gray-600 flex items-start">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full mr-2 mt-1.5 flex-shrink-0"></div>
                      <div>{reason}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 bg-gray-50">
        <button
          onClick={() => setActiveTab('accepted')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'accepted'
              ? 'bg-white text-emerald-700 border-b-2 border-emerald-500'
              : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <i className="fas fa-check-circle text-emerald-500"></i>
            <span>Accepted Sources</span>
            <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full text-xs font-bold">
              {accepted_sources.length}
            </span>
          </div>
        </button>
        <button
          onClick={() => setActiveTab('rejected')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'rejected'
              ? 'bg-white text-red-700 border-b-2 border-red-500'
              : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <i className="fas fa-times-circle text-red-500"></i>
            <span>Filtered Out</span>
            <span className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-bold">
              {rejected_sources.length}
            </span>
          </div>
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-4">
        {activeTab === 'accepted' && (
          <div className="space-y-3">
            {accepted_sources.length > 0 ? (
              <>
                <div className="text-sm text-emerald-700 font-medium mb-3 flex items-center">
                  <i className="fas fa-check-circle mr-2"></i>
                  High-quality sources selected for analysis
                </div>
                <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
                  {accepted_sources.map((source, idx) => (
                    <div key={idx} className="bg-emerald-50 border border-emerald-200 rounded-lg">
                      <SourceCard source={source} index={idx} />
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <i className="fas fa-search text-3xl mb-3 text-gray-300"></i>
                <div className="text-sm">No accepted sources yet</div>
                <div className="text-xs">Waiting for source discovery to complete...</div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'rejected' && (
          <div className="space-y-3">
            {rejected_sources.length > 0 ? (
              <>
                <div className="text-sm text-red-700 font-medium mb-3 flex items-center">
                  <i className="fas fa-times-circle mr-2"></i>
                  Sources filtered out due to quality concerns
                </div>
                
                {/* Quality Comparison Statistics */}
                <div className="bg-red-50 rounded-lg p-3 border border-red-200 mb-3">
                  <div className="text-xs font-medium text-red-700 mb-2 flex items-center">
                    <i className="fas fa-chart-bar mr-1"></i>
                    Quality Comparison: Rejected vs. Accepted Sources
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div className="text-center">
                      <div className="font-medium text-red-600">
                        {rejected_sources.length > 0 ? 
                          Math.round((rejected_sources.reduce((sum, s) => sum + (parseFloat(s.authority_score) || 0.5), 0) / rejected_sources.length) * 100) + '%'
                          : 'N/A'
                        }
                      </div>
                      <div className="text-gray-600">Rejected Authority</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-red-600">
                        {rejected_sources.length > 0 ? 
                          Math.round((rejected_sources.reduce((sum, s) => sum + (parseFloat(s.relevance_score) || 0.5), 0) / rejected_sources.length) * 100) + '%'
                          : 'N/A'
                        }
                      </div>
                      <div className="text-gray-600">Rejected Relevance</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-red-600">
                        {rejected_sources.length > 0 ? 
                          Math.round((rejected_sources.reduce((sum, s) => sum + (parseFloat(s.content_quality) || 0.5), 0) / rejected_sources.length) * 100) + '%'
                          : 'N/A'
                        }
                      </div>
                      <div className="text-gray-600">Rejected Quality</div>
                    </div>
                  </div>
                  {accepted_sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-red-200">
                      <div className="grid grid-cols-3 gap-3 text-xs">
                        <div className="text-center">
                          <div className="font-medium text-emerald-600">
                            {Math.round((accepted_sources.reduce((sum, s) => sum + (s.authority_score || 0.5), 0) / accepted_sources.length) * 100)}%
                          </div>
                          <div className="text-gray-600">Accepted Authority</div>
                        </div>
                        <div className="text-center">
                          <div className="font-medium text-emerald-600">
                            {Math.round((accepted_sources.reduce((sum, s) => sum + (s.relevance_score || 0.5), 0) / accepted_sources.length) * 100)}%
                          </div>
                          <div className="text-gray-600">Accepted Relevance</div>
                        </div>
                        <div className="text-center">
                          <div className="font-medium text-emerald-600">
                            {Math.round((accepted_sources.reduce((sum, s) => sum + (s.content_quality || 0.5), 0) / accepted_sources.length) * 100)}%
                          </div>
                          <div className="text-gray-600">Accepted Quality</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
                  {rejected_sources.map((source, idx) => (
                    <RejectedSourceCard key={idx} source={source} index={idx} />
                  ))}
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <i className="fas fa-shield-alt text-3xl mb-3 text-gray-300"></i>
                <div className="text-sm">No sources filtered out</div>
                <div className="text-xs">All discovered sources met quality standards</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Rejected Source Card Component
const RejectedSourceCard = ({ source, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const formatUrl = (url) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace('www.', '');
    } catch {
      return url;
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.7) return 'text-green-600 bg-green-100';
    if (score >= 0.5) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getFailureReasonIcon = (reason) => {
    if (reason.includes('authority')) return 'fas fa-shield-alt';
    if (reason.includes('relevance')) return 'fas fa-bullseye';
    if (reason.includes('quality')) return 'fas fa-star';
    return 'fas fa-exclamation-triangle';
  };

  return (
    <div className="bg-white rounded-lg border border-red-200 shadow-sm">
      {/* Rejected Source Header */}
      <div 
        className="flex items-start justify-between p-3 cursor-pointer hover:bg-red-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <div className="flex items-center justify-center w-6 h-6 bg-red-100 text-red-600 rounded-full text-xs font-bold">
              {index + 1}
            </div>
            <div className="text-sm font-medium text-gray-800 truncate">
              {source.title || formatUrl(source.url)}
            </div>
            <i className="fas fa-times-circle text-red-500 text-xs"></i>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
            <i className="fas fa-link text-red-400"></i>
            <a 
              href={source.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline truncate max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              {source.url}
            </a>
          </div>
          
          {/* Quality Scores */}
          <div className="flex items-center gap-2 mb-2">
            {source.authority_score !== undefined && (
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreColor(source.authority_score)}`}>
                Authority: {Math.round(source.authority_score * 100)}%
              </span>
            )}
            {source.relevance_score !== undefined && (
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreColor(source.relevance_score)}`}>
                Relevance: {Math.round(source.relevance_score * 100)}%
              </span>
            )}
            {source.content_quality !== undefined && (
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreColor(source.content_quality)}`}>
                Quality: {Math.round(source.content_quality * 100)}%
              </span>
            )}
          </div>

          {/* Failure Reasons */}
          {source.rejection_reasons && source.rejection_reasons.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {source.rejection_reasons.map((reason, idx) => (
                <span 
                  key={idx}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium"
                >
                  <i className={`${getFailureReasonIcon(reason)} text-xs`}></i>
                  <span className="capitalize">{reason.replace('_', ' ')}</span>
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex-shrink-0 ml-2">
          <i className={`fas fa-chevron-${isExpanded ? 'up' : 'down'} text-xs text-gray-400 transition-transform`}></i>
        </div>
      </div>

      {/* Expandable Details */}
      {isExpanded && (
        <div className="border-t bg-red-50 p-3">
          <div className="space-y-3">
            {/* Detailed Scores */}
            <div>
              <div className="text-xs font-medium text-gray-700 mb-2">Quality Score Breakdown:</div>
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-white rounded p-2 border border-red-200">
                  <div className="text-xs text-gray-600">Authority</div>
                  <div className={`text-sm font-bold ${source.authority_score >= 0.5 ? 'text-green-600' : 'text-red-600'}`}>
                    {source.authority_score ? Math.round(source.authority_score * 100) : 'N/A'}%
                  </div>
                </div>
                <div className="bg-white rounded p-2 border border-red-200">
                  <div className="text-xs text-gray-600">Relevance</div>
                  <div className={`text-sm font-bold ${source.relevance_score >= 0.5 ? 'text-green-600' : 'text-red-600'}`}>
                    {source.relevance_score ? Math.round(source.relevance_score * 100) : 'N/A'}%
                  </div>
                </div>
                <div className="bg-white rounded p-2 border border-red-200">
                  <div className="text-xs text-gray-600">Content</div>
                  <div className={`text-sm font-bold ${source.content_quality >= 0.5 ? 'text-green-600' : 'text-red-600'}`}>
                    {source.content_quality ? Math.round(source.content_quality * 100) : 'N/A'}%
                  </div>
                </div>
              </div>
            </div>

            {/* Rejection Explanation */}
            {source.rejection_explanation && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-1">Why was this filtered out?</div>
                <div className="text-xs text-gray-700 bg-white rounded p-3 border border-red-200">
                  {source.rejection_explanation}
                </div>
              </div>
            )}

            {/* Content Preview (if available) */}
            {(source.content || source.snippet) && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-1">Content Preview:</div>
                <div className="text-xs text-gray-600 bg-white rounded p-3 border border-red-200 max-h-32 overflow-y-auto">
                  {source.content || source.snippet}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

function App() {
  // Use the new ResearchContext for state management
  const {
    state,
    actions,
    isResearching,
    isCompleted,
    isFailed,
    getRealTimeDuration
  } = useResearchContext();
  
  const [apiConfig, setApiConfig] = useState(null);

  // Custom hooks
  const { isConnected, connect: connectWebSocket, setProgress } = useWebSocket();
  const { 
    isResearching: hookIsResearching, 
    setIsResearching,
    startResearch: hookStartResearch, 
    fetchResults,
    error: researchError 
  } = useResearch();
  const {
    modelConfig,
    agentModels,
    availableModels,
    apiKeys,
    updateAgentModel,
    saveModelConfig,
    setApiKeys,
    loadModelConfig,
    applyModelPreset
  } = useModelConfig();

  // Handlers
  const toggleArchitecture = actions.toggleArchitecture;
  const toggleApiConfig = actions.toggleApiConfig;
  const toggleModelConfig = actions.toggleModelConfig;
  const clearError = actions.clearError;

  const handleStartResearch = useCallback(async () => {
    try {
      await actions.startResearch(modelConfig, agentModels);
    } catch (error) {
      console.error('Failed to start research:', error);
    }
  }, [actions, modelConfig, agentModels]);

  // Effects
  useEffect(() => {
    if (researchError) {
      actions.setError(researchError);
    }
  }, [researchError, actions]);

  // Fetch API configuration on mount
  useEffect(() => {
    const fetchApiConfig = async () => {
      try {
        const response = await fetch('/api/config');
        if (response.ok) {
          const config = await response.json();
          setApiConfig(config);
        }
      } catch (error) {
        console.error('Failed to fetch API config:', error);
      }
    };
    
    fetchApiConfig();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <i className="fas fa-search-plus text-2xl text-indigo-600"></i>
              <h1 className="text-2xl font-bold text-gray-900">Multi-Agent Research System</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleApiConfig}
                className="flex items-center space-x-2 px-3 py-2 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
              >
                <i className="fas fa-key"></i>
                <span>API Keys</span>
              </button>
              <button
                onClick={toggleModelConfig}
                className="flex items-center space-x-2 px-3 py-2 text-sm text-purple-600 hover:text-purple-800 hover:bg-purple-50 rounded-md transition-colors"
              >
                <i className="fas fa-cogs"></i>
                <span>Agent Models</span>
              </button>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <i className="fas fa-rocket"></i>
                <span>Intelligent Parallel Processing</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <i className="fas fa-search"></i>
                <span className="text-gray-700">
                  Search: <span className="font-medium text-blue-600">
                    {(() => {
                      // Show current search engine status
                      const searchConfig = apiConfig?.search_engine;
                      if (!searchConfig) return 'Loading...';
                      
                      const preferred = searchConfig.preferred || 'brave';
                      const firecrawlAvailable = searchConfig.firecrawl_available;
                      const braveAvailable = searchConfig.brave_available;
                      
                      if (preferred === 'firecrawl' && firecrawlAvailable) {
                        return '🔥 Firecrawl (Full Content)';
                      } else if (preferred === 'brave' && braveAvailable) {
                        return '🔍 Brave Search';
                      } else if (preferred === 'auto') {
                        return firecrawlAvailable ? '🔥 Auto (Firecrawl Preferred)' : '🔍 Auto (Brave Fallback)';
                      } else {
                        return '⚠️ No Search Engine';
                      }
                    })()}
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* API Configuration Modal */}
      <ApiConfigModal 
                    show={state.showApiConfig} 
        onClose={toggleApiConfig} 
        apiKeys={apiKeys} 
        setApiKeys={setApiKeys} 
      />

      {/* Model Configuration Modal */}
      <ModelConfigModal 
                  show={state.showModelConfig} 
        onClose={toggleModelConfig} 
        modelConfig={modelConfig}
        agentModels={agentModels}
        availableModels={availableModels}
        updateAgentModel={updateAgentModel}
        saveModelConfig={saveModelConfig}
        applyModelPreset={applyModelPreset}
      />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-6">
          {/* Main Content */}
          <div className="flex-1 min-w-0 overflow-hidden">
            {/* Research Input Section */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                <i className="fas fa-lightbulb text-yellow-500 mr-2"></i>
                Start Your Research
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Research Query
                  </label>
                  <textarea
                    value={state.query}
                    onChange={(e) => actions.setQuery(e.target.value)}
                    placeholder="What would you like to research? (e.g., 'Latest developments in artificial intelligence and their impact on healthcare')"
                    className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 transition-colors ${
                      state.query.trim().length < 3 && state.query.trim().length > 0 
                        ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                        : state.query.trim().length > 1000 
                        ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                        : 'border-gray-300 focus:ring-indigo-500 focus:border-transparent'
                    }`}
                    rows="3"
                    disabled={isResearching}
                  />
                  <div className="flex justify-between items-center mt-1">
                    <div className="text-xs text-gray-500">
                      Minimum 3 characters required
                    </div>
                    <div className={`text-xs ${
                      state.query.length > 1000 ? 'text-red-500' : 
                      state.query.length > 900 ? 'text-yellow-500' : 
                      'text-gray-500'
                    }`}>
                      {state.query.length}/1000 characters
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max Sub-Questions
                      </label>
                      <select
                        value={state.maxQuestions}
                        onChange={(e) => actions.setMaxQuestions(parseInt(e.target.value))}
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 h-10"
                        disabled={isResearching}
                      >
                        <option value={3}>3 (Quick)</option>
                        <option value={5}>5 (Balanced)</option>
                        <option value={7}>7 (Comprehensive)</option>
                        <option value={10}>10 (Deep Dive)</option>
                      </select>
                    </div>
                  </div>
                  
                  {/* Model Presets Section */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Model Presets
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
                      <button
                        onClick={() => {
                          console.log('🖱️ Budget preset button clicked');
                          applyModelPreset('budget');
                        }}
                        disabled={isResearching}
                        className="px-3 py-2 text-xs bg-green-50 border border-green-200 text-green-700 rounded-md hover:bg-green-100 disabled:opacity-50 transition-colors"
                        title="Cost-effective models optimized for each agent task"
                      >
                        <i className="fas fa-piggy-bank mr-1"></i>
                        Budget
                      </button>
                      <button
                        onClick={() => applyModelPreset('balanced')}
                        disabled={isResearching}
                        className="px-3 py-2 text-xs bg-blue-50 border border-blue-200 text-blue-700 rounded-md hover:bg-blue-100 disabled:opacity-50 transition-colors"
                        title="Good balance of cost and performance with task specialization"
                      >
                        <i className="fas fa-balance-scale mr-1"></i>
                        Balanced
                      </button>
                      <button
                        onClick={() => applyModelPreset('performance')}
                        disabled={isResearching}
                        className="px-3 py-2 text-xs bg-purple-50 border border-purple-200 text-purple-700 rounded-md hover:bg-purple-100 disabled:opacity-50 transition-colors"
                        title="High-quality models specialized for each agent's role"
                      >
                        <i className="fas fa-rocket mr-1"></i>
                        Performance
                      </button>
                      <button
                        onClick={() => applyModelPreset('premium')}
                        disabled={isResearching}
                        className="px-3 py-2 text-xs bg-red-50 border border-red-200 text-red-700 rounded-md hover:bg-red-100 disabled:opacity-50 transition-colors"
                        title="Best available models for maximum quality results"
                      >
                        <i className="fas fa-crown mr-1"></i>
                        Premium
                      </button>
                    </div>
                    <div className="text-xs text-gray-500 mb-4">
                      Choose a preset to automatically configure optimal models for each agent based on their specific tasks. Hover for details.
                    </div>
                  </div>
                  
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-gray-700">
                        Agent Model Configuration
                      </label>
                      <button
                        onClick={toggleModelConfig}
                        className="text-xs text-purple-600 hover:text-purple-800 flex items-center"
                      >
                        <i className="fas fa-cogs mr-1"></i>
                        Advanced Settings
                      </button>
                    </div>
                    {modelConfig && modelConfig.agent_assignments ? (
                      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
                        {modelConfig.agent_assignments.map((agent, index) => (
                          <div key={agent.agent_type} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                            <div className="mb-2">
                              <label className="block text-xs font-medium text-gray-700 mb-1">
                                {agent.agent_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} Agent
                              </label>
                              <select
                                value={agentModels[agent.agent_type] || agent.model_name}
                                onChange={(e) => updateAgentModel(agent.agent_type, e.target.value)}
                                className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500 text-xs"
                                disabled={isResearching}
                              >
                                {modelConfig.available_models.map(model => (
                                  <option key={model} value={model}>
                                    {model.replace('accounts/fireworks/models/', '')}
                                  </option>
                                ))}
                              </select>
                            </div>
                            {(() => {
                              const selectedModel = agentModels[agent.agent_type] || agent.model_name;
                              const pricing = modelConfig.model_pricing[selectedModel];
                              return pricing ? (
                                <div className="text-xs text-gray-500">
                                  ${pricing.input}/${pricing.output} per 1M
                                </div>
                              ) : null;
                            })()}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600 mx-auto mb-2"></div>
                        <div className="text-xs text-gray-600">Loading agent configurations...</div>
                      </div>
                    )}
                    <div className="text-xs text-gray-500 mt-2">
                      Each agent uses a specialized AI model optimized for its task. Changes apply to the current research session.
                    </div>
                  </div>
                </div>
                
                {/* Research Button on its own row */}
                <div className="mt-4">
                  <button
                    onClick={handleStartResearch}
                    disabled={isResearching || !state.query || !state.query.trim()}
                    className="w-full bg-indigo-600 text-white px-6 py-3 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-lg font-medium"
                  >
                    {isResearching ? (
                      <>
                        <i className="fas fa-spinner fa-spin mr-2"></i>
                        Researching...
                      </>
                    ) : (
                      <>
                        <i className="fas fa-search mr-2"></i>
                        Start Research
                      </>
                    )}
                  </button>
                </div>
              </div>
              
              {/* Error Display */}
              {state.error && (
                <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
                  <div className="flex items-center justify-between">
                    <span>{state.error}</span>
                    <button onClick={clearError} className="text-red-500 hover:text-red-700">
                      <i className="fas fa-times"></i>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Pipeline Visualization */}
            {(isResearching || state.progress) && (
              <div className="bg-white rounded-lg shadow-md p-6 mb-8">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  <i className="fas fa-cogs text-blue-500 mr-2"></i>
                  Research Pipeline
                </h3>
                <PipelineFlow progress={state.progress} />
              </div>
            )}



            {/* Progress Display */}
            {state.progress && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6 mb-6 shadow-sm">
                <h3 className="text-lg font-semibold text-blue-900 mb-4">
                  <i className="fas fa-cogs text-blue-600 mr-2"></i>
                  Research Progress
                </h3>
                
                <div className="space-y-4">
                  {/* Main Progress Bar */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-blue-700">
                      {state.progress.stage || 'Processing...'}
                    </span>
                    <span className="text-sm text-blue-600 font-semibold">
                      {state.progress.progress_percentage || 0}%
                    </span>
                  </div>
                  
                  <div className="w-full bg-blue-200 rounded-full h-3 shadow-inner">
                    <div 
                      className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-700 shadow-sm"
                      style={{width: `${state.progress.progress_percentage || 0}%`}}
                    ></div>
                  </div>
                  
                  {/* Current Operation */}
                  {state.progress.current_operation && (
                    <div className="flex items-center text-sm text-blue-700 bg-white p-2 rounded border border-blue-100">
                      <i className="fas fa-arrow-right mr-2 text-blue-500"></i>
                      <span className="font-medium">{state.progress.current_operation}</span>
                    </div>
                  )}
                  
                  {/* Real-time Token & Cost Tracking */}
                  {(state.progress.tokens_used || state.progress.estimated_cost || state.progress.api_calls_made) && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                      <div className="bg-white p-3 rounded-lg border border-green-100 text-center">
                        <div className="text-lg font-bold text-green-600">
                          {state.progress.tokens_used || 0}
                        </div>
                        <div className="text-xs text-green-700 font-medium">Tokens Used</div>
                      </div>
                      <div className="bg-white p-3 rounded-lg border border-purple-100 text-center">
                        <div className="text-lg font-bold text-purple-600">
                          {typeof state.progress.estimated_cost === 'number' ? `$${state.progress.estimated_cost.toFixed(4)}` : 
                           typeof state.progress.estimated_cost === 'string' ? state.progress.estimated_cost : '$0.0000'}
                        </div>
                        <div className="text-xs text-purple-700 font-medium">Estimated Cost</div>
                      </div>
                      <div className="bg-white p-3 rounded-lg border border-orange-100 text-center">
                        <div className="text-lg font-bold text-orange-600">
                          {state.progress.api_calls_made || 0}
                        </div>
                        <div className="text-xs text-orange-700 font-medium">API Calls</div>
                      </div>
                      <div className="bg-white p-3 rounded-lg border border-blue-100 text-center">
                        <div className="text-lg font-bold text-blue-600">
                          {getRealTimeDuration()}
                        </div>
                        <div className="text-xs text-blue-700 font-medium">Duration</div>
                      </div>
                    </div>
                  )}
                  
                  {/* Completion Message */}
                  {state.progress.status === 'completed' && (
                    <div className="bg-white p-4 rounded-lg shadow-sm border border-green-200 mt-4">
                      <div className="flex items-center space-x-2">
                        <i className="fas fa-check-circle text-green-500"></i>
                        <span className="text-sm font-medium text-gray-700">
                          Research completed successfully with {state.progress.final_metrics?.steps_completed || state.progress.steps_completed || 0} steps
                        </span>
                      </div>
                    </div>
                  )}
                  
                  {/* Stage Progress Breakdown */}
                  {state.progress.stage_breakdown && (
                    <div className="mt-4">
                      <div className="text-xs font-semibold text-blue-700 mb-3">
                        Research Pipeline Stages
                      </div>
                      <div className="space-y-2">
                        {state.progress.stage_breakdown.map((stage, idx) => (
                          <StageCard key={idx} stage={stage} stageIndex={idx} progress={state.progress} />
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Parallel Operations */}
                  {state.progress.parallel_operations && state.progress.parallel_operations.length > 0 && (
                    <div className="mt-4">
                      <div className="text-xs font-semibold text-blue-700 mb-2">
                        <i className="fas fa-layer-group mr-1"></i>
                        Parallel Operations ({state.progress.parallel_operations.length})
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                        {state.progress.parallel_operations.map((op, idx) => (
                          <div key={idx} className="bg-white p-3 rounded-lg border border-gray-100 shadow-sm">
                            <div className="flex items-center justify-between mb-1">
                              <div className="text-xs font-medium text-gray-700">{op.agent}</div>
                              <div className={`w-2 h-2 rounded-full ${
                                op.status === 'completed' ? 'bg-green-500' :
                                op.status === 'processing' ? 'bg-blue-500 animate-pulse' :
                                'bg-yellow-500'
                              }`}></div>
                            </div>
                            <div className="text-xs text-gray-600">{op.status}</div>
                            {op.tokens_used && (
                              <div className="text-xs text-green-600 mt-1">
                                {op.tokens_used} tokens
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            
            {/* Performance Analytics Display */}
            {state.results && (
              <div className="bg-white rounded-lg shadow-md p-6 max-w-full overflow-hidden">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">
                  <i className="fas fa-analytics text-purple-500 mr-2"></i>
                  Performance Analytics
                </h3>
                <div className="text-sm text-gray-600 mb-4">
                  <i className="fas fa-info-circle mr-1"></i>
                  System performance metrics and export options. For research findings, see the <strong>Report Assembly</strong> section above.
                </div>
                
                {/* Quality Score */}
                {state.results.confidence_score && (
                  <div className="mb-6 flex items-center space-x-4">
                    <div className="flex items-center">
                      <span className="text-sm font-medium text-gray-700 mr-2">Quality Score:</span>
                      <div className="flex items-center">
                        <div className="w-20 bg-gray-200 rounded-full h-2 mr-2">
                          <div 
                            className="bg-green-500 h-2 rounded-full"
                            style={{width: `${state.results.confidence_score * 100}%`}}
                          ></div>
                        </div>
                        <span className="text-sm font-semibold">
                          {(state.results.confidence_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Export Options */}
                <div className="mb-6 flex space-x-3">
                  <button 
                                          onClick={() => window.open(`/api/research/${state.currentSession}/export/pdf`)}
                    className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition-colors"
                  >
                    <i className="fas fa-file-pdf mr-2"></i>
                    Export PDF
                  </button>
                  <button 
                                          onClick={() => window.open(`/api/research/${state.currentSession}/export/html`)}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
                  >
                    <i className="fas fa-file-code mr-2"></i>
                    Export HTML
                  </button>
                  <button 
                    onClick={() => {
                      const dataStr = JSON.stringify(state.results, null, 2);
                      const dataBlob = new Blob([dataStr], {type: 'application/json'});
                      const url = URL.createObjectURL(dataBlob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = `research_data_${state.currentSession}.json`;
                      link.click();
                    }}
                    className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors"
                    title="Download raw research data and metrics"
                  >
                    <i className="fas fa-download mr-2"></i>
                    Download Raw Data
                  </button>
                </div>
                
                {/* Metrics Dashboard */}
                {state.metrics && (
                  <div className="mb-6 bg-gray-50 rounded-lg p-6 animate-fade-in">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">
                      <i className="fas fa-analytics text-purple-600 mr-2"></i>
                      Performance Metrics
                    </h4>
                    
                    {/* Overall Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-2xl font-bold text-blue-600">{state.metrics.total_duration}</div>
                        <div className="text-sm text-gray-600">Total Time</div>
                      </div>
                      <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-2xl font-bold text-green-600">{state.metrics.total_tokens}</div>
                        <div className="text-sm text-gray-600">Total Tokens</div>
                      </div>
                      <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-2xl font-bold text-purple-600">{state.metrics.total_cost}</div>
                        <div className="text-sm text-gray-600">Total Cost</div>
                      </div>
                      <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-2xl font-bold text-orange-600">{state.metrics.cache_hit_rate}</div>
                        <div className="text-sm text-gray-600">Cache Hit Rate</div>
                      </div>
                    </div>
                    
                    {/* Performance Insights */}
                    {state.metrics.insights && (
                      <div className="mb-6">
                        <h5 className="text-md font-semibold text-gray-800 mb-3">Performance Insights</h5>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="bg-white p-4 rounded-lg shadow">
                            <div className="text-sm font-medium text-gray-700">Slowest Step</div>
                            <div className="text-lg font-semibold text-red-600">{state.metrics.insights.slowest_step.name}</div>
                            <div className="text-sm text-gray-600">{state.metrics.insights.slowest_step.duration} - {state.metrics.insights.slowest_step.agent}</div>
                          </div>
                          <div className="bg-white p-4 rounded-lg shadow">
                            <div className="text-sm font-medium text-gray-700">Most Expensive Step</div>
                            <div className="text-lg font-semibold text-yellow-600">{state.metrics.insights.most_expensive_step.name}</div>
                            <div className="text-sm text-gray-600">{state.metrics.insights.most_expensive_step.cost} - {state.metrics.insights.most_expensive_step.agent}</div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Enhanced Step Breakdown with Token Details */}
                    {state.metrics.steps && (
                      <div className="mb-6 h-96 overflow-y-auto bg-gray-50 rounded-lg p-4 scrollbar-thin">
                        <h5 className="text-md font-semibold text-gray-800 mb-3">
                          <i className="fas fa-list-ol text-blue-600 mr-2"></i>
                          Detailed Step Breakdown
                        </h5>
                        <div className="space-y-4">
                          {state.metrics.steps.map((step, idx) => (
                            <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center space-x-3">
                                  <div className="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-600 rounded-full text-sm font-semibold">
                                    {idx + 1}
                                  </div>
                                  <div>
                                    <h6 className="text-sm font-semibold text-gray-900">{step.step_name}</h6>
                                    <p className="text-xs text-gray-500">{step.agent}</p>
                                    {step.model_used && (
                                      <p className="text-xs text-blue-600 font-medium">
                                        <i className="fas fa-robot mr-1"></i>
                                        {step.model_used}
                                      </p>
                                    )}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <div className="text-sm font-semibold text-gray-900">{step.duration}</div>
                                  <div className="text-xs text-gray-500">{step.api_calls} API calls</div>
                                </div>
                              </div>
                              
                              {/* Token Usage Breakdown */}
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                                <div className="bg-green-50 p-2 rounded border border-green-100">
                                  <div className="text-sm font-bold text-green-700">{step.total_tokens}</div>
                                  <div className="text-xs text-green-600">Total Tokens</div>
                                </div>
                                <div className="bg-blue-50 p-2 rounded border border-blue-100">
                                  <div className="text-sm font-bold text-blue-700">{step.prompt_tokens || 'N/A'}</div>
                                  <div className="text-xs text-blue-600">Prompt Tokens</div>
                                </div>
                                <div className="bg-purple-50 p-2 rounded border border-purple-100">
                                  <div className="text-sm font-bold text-purple-700">{step.completion_tokens || 'N/A'}</div>
                                  <div className="text-xs text-purple-600">Completion Tokens</div>
                                </div>
                                <div className="bg-yellow-50 p-2 rounded border border-yellow-100">
                                  <div className="text-sm font-bold text-yellow-700">{step.cost}</div>
                                  <div className="text-xs text-yellow-600">Cost</div>
                                </div>
                              </div>
                              
                              {/* Token Usage Bar */}
                              {step.prompt_tokens && step.completion_tokens && step.total_tokens && (
                                <div className="mb-3">
                                  <div className="flex justify-between text-xs text-gray-600 mb-1">
                                    <span>Token Distribution</span>
                                    <span>{step.total_tokens} total</span>
                                  </div>
                                  <div className="flex h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div 
                                      className="bg-blue-500" 
                                      style={{width: `${(() => {
                                        const promptTokens = parseInt(step.prompt_tokens) || 0;
                                        const completionTokens = parseInt(step.completion_tokens) || 0;
                                        const totalTokens = promptTokens + completionTokens;
                                        return totalTokens > 0 ? Math.max(0, Math.min(100, (promptTokens / totalTokens) * 100)) : 0;
                                      })()}%`}}
                                      title={`Prompt: ${step.prompt_tokens} tokens`}
                                    ></div>
                                    <div 
                                      className="bg-purple-500" 
                                      style={{width: `${(() => {
                                        const promptTokens = parseInt(step.prompt_tokens) || 0;
                                        const completionTokens = parseInt(step.completion_tokens) || 0;
                                        const totalTokens = promptTokens + completionTokens;
                                        return totalTokens > 0 ? Math.max(0, Math.min(100, (completionTokens / totalTokens) * 100)) : 0;
                                      })()}%`}}
                                      title={`Completion: ${step.completion_tokens} tokens`}
                                    ></div>
                                  </div>
                                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                                    <span>Prompt ({(() => {
                                      const promptTokens = parseInt(step.prompt_tokens) || 0;
                                      const completionTokens = parseInt(step.completion_tokens) || 0;
                                      const totalTokens = promptTokens + completionTokens;
                                      return totalTokens > 0 ? ((promptTokens / totalTokens) * 100).toFixed(1) : '0';
                                    })()}%)</span>
                                    <span>Completion ({(() => {
                                      const promptTokens = parseInt(step.prompt_tokens) || 0;
                                      const completionTokens = parseInt(step.completion_tokens) || 0;
                                      const totalTokens = promptTokens + completionTokens;
                                      return totalTokens > 0 ? ((completionTokens / totalTokens) * 100).toFixed(1) : '0';
                                    })()}%)</span>
                                  </div>
                                </div>
                              )}
                              
                              {/* Performance Indicators */}
                              <div className="flex items-center justify-between text-xs">
                                <div className="flex items-center space-x-3">
                                  <span className={`px-2 py-1 rounded-full ${
                                    step.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                  }`}>
                                    {step.success ? 'Success' : 'Failed'}
                                  </span>
                                  {step.cache_hits > 0 && (
                                    <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
                                      {step.cache_hits} Cache Hits
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Note: Raw JSON Results section removed - users can now access comprehensive report in Report Assembly section */}
              </div>
            )}
          </div>
          
          {/* Show Architecture Button (when hidden) */}
          {!state.showArchitecture && (
            <div className="fixed top-32 right-6 z-20">
              <button
                onClick={toggleArchitecture}
                className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 flex items-center space-x-2"
                title="Show System Architecture"
              >
                <i className="fas fa-network-wired"></i>
                <span>Show Architecture</span>
              </button>
            </div>
          )}
          
          {/* Architecture Sidebar */}
          <ArchitectureSidebar 
            show={state.showArchitecture} 
            onToggle={toggleArchitecture} 
            progress={state.progress} 
          />
        </div>
      </main>
    </div>
  );
}

// Wrap in ErrorBoundary for production
function AppWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}

export default AppWithErrorBoundary; 