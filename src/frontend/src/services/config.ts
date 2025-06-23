import { apiClient } from '@/lib/api';

export interface ChunkConfig {
  strategy: string;
  chunk_size: number;
  chunk_overlap: number;
  min_chunk_size: number;
  max_chunk_size: number;
  separators: string[];
  use_semantic_chunking: boolean;
  semantic_threshold: number;
}

export interface IndexConfig {
  model_name: string;
  model_type: string;
  dimensions: number;
  index_type: string;
  similarity_metric: string;
  use_vector_db: boolean;
  use_bm25: boolean;
  top_n_retrieval: number;
}

export interface GlobalConfig {
  chunk_config: ChunkConfig;
  index_config: IndexConfig;
}

export interface BulkProcessingStatus {
  is_running: boolean;
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  current_document?: string;
  started_at?: string;
  estimated_completion?: string;
}

class ConfigService {
  /**
   * Get current global processing configuration
   */
  async getGlobalConfig(): Promise<GlobalConfig> {
    const response = await apiClient.get('/config/global');
    return response.data;
  }

  /**
   * Update global processing configuration
   */
  async updateGlobalConfig(config: GlobalConfig): Promise<{ message: string }> {
    const response = await apiClient.put('/config/global', config);
    return response.data;
  }

  /**
   * Get current chunk configuration
   */
  async getChunkConfig(): Promise<ChunkConfig> {
    const response = await apiClient.get('/config/chunk');
    return response.data;
  }

  /**
   * Get current index configuration
   */
  async getIndexConfig(): Promise<IndexConfig> {
    const response = await apiClient.get('/config/index');
    return response.data;
  }

  /**
   * Apply current global configuration to all documents
   */
  async applyGlobalConfigToAll(): Promise<{ message: string }> {
    const response = await apiClient.post('/config/apply-to-all');
    return response.data;
  }

  /**
   * Get bulk processing status
   */
  async getBulkProcessingStatus(): Promise<BulkProcessingStatus> {
    const response = await apiClient.get('/config/bulk-status');
    return response.data;
  }

  /**
   * Invalidate configuration cache (admin only)
   */
  async invalidateCache(): Promise<{ message: string }> {
    const response = await apiClient.post('/config/invalidate-cache');
    return response.data;
  }
}

export const configService = new ConfigService(); 