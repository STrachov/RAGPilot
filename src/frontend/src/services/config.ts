import { apiClient } from '@/lib/api';
import { ParseConfig, ChunkingConfig, IndexConfig, GlobalConfig } from '@/types/ragpilot';

export interface ConfigStatus {
  config_file_exists: boolean;
  config_file_path: string;
  config_file_size: number;
  cache_status: string;
  last_modified?: number;
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
   * Get current parse configuration
   */
  async getParseConfig(): Promise<ParseConfig> {
    const response = await apiClient.get('/config/parse');
    return response.data;
  }

  /**
   * Get current chunk configuration
   */
  async getChunkConfig(): Promise<ChunkingConfig> {
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
   * Invalidate configuration cache (admin only)
   */
  async invalidateCache(): Promise<{ message: string }> {
    const response = await apiClient.post('/config/invalidate-cache');
    return response.data;
  }

  /**
   * Force reload configuration from file
   */
  async reloadConfig(): Promise<{ message: string }> {
    const response = await apiClient.post('/config/reload');
    return response.data;
  }

  /**
   * Create a backup of current configuration
   */
  async backupConfig(): Promise<{ message: string }> {
    const response = await apiClient.post('/config/backup');
    return response.data;
  }

  /**
   * Get configuration system status
   */
  async getConfigStatus(): Promise<ConfigStatus> {
    const response = await apiClient.get('/config/status');
    return response.data;
  }
}

export const configService = new ConfigService(); 