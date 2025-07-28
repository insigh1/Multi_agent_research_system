import { useState, useCallback, useEffect } from 'react';
import { api } from '../utils/api';

export const useModelConfig = () => {
  const [selectedModel, setSelectedModel] = useState('llama-v3p1-8b-instruct');
  const [availableModels, setAvailableModels] = useState([]);
  const [agentModels, setAgentModels] = useState({});
  const [modelConfig, setModelConfig] = useState(null);
  const [showModelConfig, setShowModelConfig] = useState(false);
  const [error, setError] = useState(null);
  
  // API Keys state management
  const [apiKeys, setApiKeys] = useState(() => {
    try {
      const saved = localStorage.getItem('apiKeys');
      return saved ? JSON.parse(saved) : { fireworks: '', brave: '', firecrawl: '' };
    } catch {
      return { fireworks: '', brave: '', firecrawl: '' };
    }
  });

  // Save API keys to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('apiKeys', JSON.stringify(apiKeys));
  }, [apiKeys]);

  const loadModelConfig = useCallback(async () => {
    try {
      const data = await api.getModelConfig();
      if (data.success) {
        setModelConfig(data);
        // Initialize agentModels state with current configuration
        const currentAgentModels = {};
        data.agent_assignments.forEach(agent => {
          currentAgentModels[agent.agent_type] = agent.model_name;
        });
        setAgentModels(currentAgentModels);
      }
    } catch (error) {
      console.error('Failed to load model configuration:', error);
    }
  }, []);

  const updateAgentModel = useCallback((agentType, modelName) => {
    setAgentModels(prev => ({
      ...prev,
      [agentType]: modelName
    }));
  }, []);

  const saveModelConfig = useCallback(async () => {
    try {
      const data = await api.updateModelConfig(agentModels);
      if (data.success) {
        setModelConfig(data.updated_config);
        setError(null);
      } else {
        setError(data.error);
      }
    } catch (error) {
      setError('Failed to save model configuration: ' + error.message);
    }
  }, [agentModels]);

  const toggleModelConfig = useCallback(() => {
    setShowModelConfig(prev => !prev);
  }, []);

  const applyModelPreset = useCallback((presetType) => {
    console.log('🎯 Applying preset:', presetType);
    console.log('📋 Current modelConfig:', modelConfig);
    console.log('🤖 Current agentModels:', agentModels);
    
    if (!modelConfig || !modelConfig.agent_assignments) {
      console.warn('❌ No modelConfig or agent_assignments available');
      return;
    }
    
    // Get list of available models with full paths
    const availableFullModels = modelConfig.available_models || [];
    console.log('📦 Available models:', availableFullModels);
    console.log('📊 Total available models:', availableFullModels.length);
    
    // Function to find the best available model from a list
    const findBestAvailableModel = (modelList) => {
      for (const model of modelList) {
        if (availableFullModels.includes(model)) {
          return model;
        }
      }
      // Fallback to first available model if none of the preset models are available
      return availableFullModels[0] || modelList[0];
    };
    
    // Define task-specific model assignments for each preset based on available models (no prefix)
    const presets = {
      budget: {
        // Budget models (~$0.20/1M tokens) optimized for each agent's task
        research_planner: ['qwen3-8b', 'qwen2-7b-instruct'], // Best reasoning in budget tier
        web_search: ['llama-v3p1-8b-instruct', 'qwen2-7b-instruct'], // Fast & efficient search
        quality_evaluation: ['qwen3-8b', 'qwen2-7b-instruct'], // Better analysis capability
        summarization: ['qwen2-7b-instruct', 'llama-v3p1-8b-instruct'], // Good synthesis
        report_synthesis: ['qwen3-8b', 'qwen2-7b-instruct'] // Best writing in budget tier
      },
      balanced: {
        // Mid-tier models (~$0.15-0.90/1M) with task specialization
        research_planner: ['qwen3-30b-a3b', 'llama4-scout-instruct-basic'], // Strong reasoning
        web_search: ['llama-v3p1-8b-instruct', 'qwen3-8b'], // Keep search fast
        quality_evaluation: ['qwen3-235b-a22b', 'qwen3-30b-a3b'], // Strong analytical models
        summarization: ['qwen3-30b-a3b', 'llama4-scout-instruct-basic'], // Good synthesis
        report_synthesis: ['llama4-maverick-instruct-basic', 'qwen3-235b-a22b'] // Better writing capability
      },
      performance: {
        // High-performance models (~$0.90/1M) specialized for each task
        research_planner: ['qwq-32b', 'llama-v3p3-70b-instruct'], // Advanced reasoning models
        web_search: ['qwen3-30b-a3b', 'llama-v3p1-8b-instruct'], // Efficient but capable
        quality_evaluation: ['llama-v3p3-70b-instruct', 'qwen2p5-72b-instruct'], // Superior analysis
        summarization: ['llama-v3p3-70b-instruct', 'llama-v3p1-70b-instruct'], // Excellent synthesis
        report_synthesis: ['llama-v3p3-70b-instruct', 'qwen2p5-72b-instruct'] // Top-tier writing
      },
      premium: {
        // Premium models ($1.20+ per 1M tokens) for maximum quality
        research_planner: ['deepseek-r1-basic', 'llama-v3p1-405b-instruct'], // Ultimate reasoning
        web_search: ['qwen3-30b-a3b', 'llama4-scout-instruct-basic'], // Still efficient
        quality_evaluation: ['deepseek-r1', 'llama-v3p1-405b-instruct'], // Best analysis available
        summarization: ['llama-v3p1-405b-instruct', 'deepseek-r1-basic'], // Premium synthesis
        report_synthesis: ['deepseek-r1', 'llama-v3p1-405b-instruct'] // Ultimate writing quality
      }
    };
    
    const preset = presets[presetType];
    if (!preset) {
      console.warn('❌ Unknown preset type:', presetType);
      return;
    }
    
    console.log('🎨 Using preset configuration:', preset);
    
    // Create new agent model assignments with task-specific models
    const newAgentModels = {};
    
    modelConfig.agent_assignments.forEach(agent => {
      const agentType = agent.agent_type;
      console.log(`🔍 Processing agent: ${agentType}`);
      
      const candidateModels = preset[agentType] || preset.research_planner; // Fallback to planner models
      console.log(`📝 Candidate models for ${agentType}:`, candidateModels);
      
      // Check which candidate models are actually available
      const availableCandidates = candidateModels.filter(model => availableFullModels.includes(model));
      console.log(`✅ Available candidates for ${agentType}:`, availableCandidates);
      
      const selectedModel = findBestAvailableModel(candidateModels);
      console.log(`🎯 Selected model for ${agentType}: ${selectedModel}`);
      console.log(`🔍 Model exists in available list?`, availableFullModels.includes(selectedModel));
      
      newAgentModels[agentType] = selectedModel;
    });
    
    console.log('🚀 New agent models configuration:', newAgentModels);
    console.log('🔄 About to update agent models state...');
    
    // Update the agent models state
    setAgentModels(newAgentModels);
    
    console.log('✅ Preset applied successfully!');
    console.log('🎯 State should update to:', newAgentModels);
  }, [modelConfig, agentModels]);

  // Debug logging when agentModels state changes
  useEffect(() => {
    console.log('🔄 agentModels state changed:', agentModels);
  }, [agentModels]);

  useEffect(() => {
    // Fetch available models
    api.getModels()
      .then(data => {
        if (data.models) {
          setAvailableModels(data.models);
          if (data.default_model) {
            setSelectedModel(data.default_model);
          }
        }
      })
      .catch(error => {
        console.error('Failed to fetch models:', error);
      });
    
    // Load model configuration
    loadModelConfig();
  }, [loadModelConfig]);

  return {
    selectedModel,
    setSelectedModel,
    availableModels,
    agentModels,
    modelConfig,
    showModelConfig,
    error,
    setError,
    updateAgentModel,
    saveModelConfig,
    toggleModelConfig,
    loadModelConfig,
    applyModelPreset,
    apiKeys,
    setApiKeys
  };
}; 