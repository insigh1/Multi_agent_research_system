export const PIPELINE_STEPS = [
    { name: 'Planning', icon: '🧠', stage: 'Research Planning', description: 'Analyze query & create plan', agent: 'Planner Agent' },
    { name: 'Gathering', icon: '🔍', stage: 'Information Gathering', description: 'Search & collect data', agent: 'Search Agent' },
    { name: 'Quality Check', icon: '✅', stage: 'Quality Evaluation', description: 'Evaluate quality & relevance', agent: 'Quality Agent' },
    { name: 'Analysis', icon: '📊', stage: 'Content Summarization', description: 'Summarize & analyze', agent: 'Analysis Agent' },
    { name: 'Synthesis', icon: '📝', stage: 'Report Assembly', description: 'Generate & format report', agent: 'Report Agent' }
];

export const AGENT_LIST = [
    { name: 'Research Planner', icon: '🧠' },
    { name: 'Web Retriever', icon: '🔍' },
    { name: 'Quality Evaluator', icon: '⚖️' },
    { name: 'Summarizer', icon: '📊' },
    { name: 'Report Synthesizer', icon: '📝' }
];

export const SYSTEM_COMPONENTS = [
    { name: 'FastAPI', icon: '🚀' },
    { name: 'SQLite DB', icon: '💾' },
    { name: 'Redis Cache', icon: '⚡' },
    { name: 'Fireworks AI', icon: '🤖' },
    { name: 'Web APIs', icon: '🌐' }
]; 