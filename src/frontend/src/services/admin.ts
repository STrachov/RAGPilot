import { apiClient, API_ENDPOINTS } from '@/lib/api';
import {
  SystemStats,
  ChunkingConfig,
  EmbeddingConfig,
  IndexConfig,
  RetrievalStrategy,
  LLMConfig,
  PromptTemplates
} from '@/types/ragpilot';

export const adminService = {
  // Get system statistics
  async getSystemStats(): Promise<SystemStats> {
    const { data } = await apiClient.get(API_ENDPOINTS.ADMIN.STATS);
    return data;
  },

  // Configuration management
  config: {
    // Chunking configuration
    async getChunkingConfig(): Promise<ChunkingConfig> {
      const { data } = await apiClient.get(API_ENDPOINTS.ADMIN.CONFIG.CHUNKING);
      return data;
    },

    async updateChunkingConfig(config: ChunkingConfig): Promise<{ message: string; config: ChunkingConfig }> {
      const { data } = await apiClient.post(API_ENDPOINTS.ADMIN.CONFIG.CHUNKING, config);
      return data;
    },

    // Embedding configuration
    async getEmbeddingConfig(): Promise<EmbeddingConfig> {
      const { data } = await apiClient.get(API_ENDPOINTS.ADMIN.CONFIG.EMBEDDING);
      return data;
    },

    async updateEmbeddingConfig(config: EmbeddingConfig): Promise<{ message: string; config: EmbeddingConfig }> {
      const { data } = await apiClient.post(API_ENDPOINTS.ADMIN.CONFIG.EMBEDDING, config);
      return data;
    },

    // Index configuration
    async getIndexConfig(): Promise<IndexConfig> {
      const { data } = await apiClient.get(API_ENDPOINTS.ADMIN.CONFIG.INDEX);
      return data;
    },

    async updateIndexConfig(config: IndexConfig): Promise<{ message: string; config: IndexConfig }> {
      const { data } = await apiClient.post(API_ENDPOINTS.ADMIN.CONFIG.INDEX, config);
      return data;
    },

    // Retrieval strategy
    async getRetrievalStrategy(): Promise<RetrievalStrategy> {
      const { data } = await apiClient.get(API_ENDPOINTS.ADMIN.CONFIG.RETRIEVAL);
      return data;
    },

    async updateRetrievalStrategy(config: RetrievalStrategy): Promise<{ message: string; config: RetrievalStrategy }> {
      const { data } = await apiClient.post(API_ENDPOINTS.ADMIN.CONFIG.RETRIEVAL, config);
      return data;
    },

    // LLM configuration
    async getLLMConfig(): Promise<LLMConfig> {
      const { data } = await apiClient.get(API_ENDPOINTS.ADMIN.CONFIG.LLM);
      return data;
    },

    async updateLLMConfig(config: LLMConfig): Promise<{ message: string; config: LLMConfig }> {
      const { data } = await apiClient.post(API_ENDPOINTS.ADMIN.CONFIG.LLM, config);
      return data;
    },

    // Prompt templates
    async getPromptTemplates(): Promise<PromptTemplates> {
      const { data } = await apiClient.get(API_ENDPOINTS.ADMIN.CONFIG.PROMPTS);
      return data;
    },

    async updatePromptTemplates(templates: PromptTemplates): Promise<{ message: string; templates: PromptTemplates }> {
      const { data } = await apiClient.post(API_ENDPOINTS.ADMIN.CONFIG.PROMPTS, templates);
      return data;
    },
  },
}; 