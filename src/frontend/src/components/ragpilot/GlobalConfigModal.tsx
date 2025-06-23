"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { configService } from "@/services/config";

interface GlobalConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ChunkConfig {
  strategy: string;
  chunk_size: number;
  chunk_overlap: number;
  min_chunk_size: number;
  max_chunk_size: number;
  separators: string[];
  use_semantic_chunking: boolean;
  semantic_threshold: number;
}

interface IndexConfig {
  model_name: string;
  model_type: string;
  dimensions: number;
  index_type: string;
  similarity_metric: string;
  use_vector_db: boolean;
  use_bm25: boolean;
  top_n_retrieval: number;
}

interface GlobalConfig {
  chunk_config: ChunkConfig;
  index_config: IndexConfig;
}

export const GlobalConfigModal: React.FC<GlobalConfigModalProps> = ({
  isOpen,
  onClose
}) => {
  const [config, setConfig] = useState<GlobalConfig | null>(null);
  const [isApplyingToAll, setIsApplyingToAll] = useState(false);
  const queryClient = useQueryClient();

  // Fetch current global configuration
  const { data: globalConfig, isLoading } = useQuery({
    queryKey: ['globalConfig'],
    queryFn: () => configService.getGlobalConfig(),
    enabled: isOpen,
  });

  // Update local state when data is fetched
  useEffect(() => {
    if (globalConfig) {
      setConfig(globalConfig);
    }
  }, [globalConfig]);

  // Mutation for updating global configuration
  const updateConfigMutation = useMutation({
    mutationFn: (newConfig: GlobalConfig) => configService.updateGlobalConfig(newConfig),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['globalConfig'] });
      alert('Global configuration updated successfully!');
    },
    onError: (error: any) => {
      console.error('Failed to update global configuration:', error);
      alert(`Failed to update configuration: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  // Mutation for applying configuration to all documents
  const applyToAllMutation = useMutation({
    mutationFn: () => configService.applyGlobalConfigToAll(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setIsApplyingToAll(false);
      alert('Global configuration is being applied to all documents. This may take a few minutes.');
    },
    onError: (error: any) => {
      console.error('Failed to apply configuration to all documents:', error);
      setIsApplyingToAll(false);
      alert(`Failed to apply configuration: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  const handleSave = () => {
    if (!config) return;
    updateConfigMutation.mutate(config);
  };

  const handleApplyToAll = () => {
    if (confirm('This will reprocess all documents with the current global configuration. This may take a while. Continue?')) {
      setIsApplyingToAll(true);
      applyToAllMutation.mutate();
    }
  };

  const updateChunkConfig = (field: keyof ChunkConfig, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      chunk_config: {
        ...config.chunk_config,
        [field]: value
      }
    });
  };

  const updateIndexConfig = (field: keyof IndexConfig, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      index_config: {
        ...config.index_config,
        [field]: value
      }
    });
  };

  if (!isOpen) return null;

  const modalContent = (
    <div className="fixed inset-0 flex items-center justify-center p-4" style={{ zIndex: 9999999, backgroundColor: 'rgba(0, 0, 0, 0.5)' }}>
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-gray-200 dark:border-gray-700">
        <div className="p-6">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Global Processing Configuration
            </h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : config ? (
            <div className="space-y-8">
              {/* Chunk Configuration */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Chunk Configuration
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Strategy
                    </label>
                    <select
                      value={config.chunk_config.strategy}
                      onChange={(e) => updateChunkConfig('strategy', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="recursive">Recursive</option>
                      <option value="semantic">Semantic</option>
                      <option value="fixed">Fixed Size</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Chunk Size
                    </label>
                    <input
                      type="number"
                      value={config.chunk_config.chunk_size}
                      onChange={(e) => updateChunkConfig('chunk_size', parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      min="100"
                      max="4000"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Chunk Overlap
                    </label>
                    <input
                      type="number"
                      value={config.chunk_config.chunk_overlap}
                      onChange={(e) => updateChunkConfig('chunk_overlap', parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      min="0"
                      max="1000"
                    />
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="semantic-chunking"
                      checked={config.chunk_config.use_semantic_chunking}
                      onChange={(e) => updateChunkConfig('use_semantic_chunking', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="semantic-chunking" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Use Semantic Chunking
                    </label>
                  </div>
                </div>
              </div>

              {/* Index Configuration */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Index Configuration
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Model Name
                    </label>
                    <select
                      value={config.index_config.model_name}
                      onChange={(e) => updateIndexConfig('model_name', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="sentence-transformers/all-MiniLM-L6-v2">all-MiniLM-L6-v2 (384d)</option>
                      <option value="sentence-transformers/all-mpnet-base-v2">all-mpnet-base-v2 (768d)</option>
                      <option value="text-embedding-ada-002">OpenAI Ada-002 (1536d)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Index Type
                    </label>
                    <select
                      value={config.index_config.index_type}
                      onChange={(e) => updateIndexConfig('index_type', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="faiss">FAISS</option>
                      <option value="chroma">Chroma</option>
                      <option value="pinecone">Pinecone</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Similarity Metric
                    </label>
                    <select
                      value={config.index_config.similarity_metric}
                      onChange={(e) => updateIndexConfig('similarity_metric', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="cosine">Cosine</option>
                      <option value="euclidean">Euclidean</option>
                      <option value="dot_product">Dot Product</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Top N Retrieval
                    </label>
                    <input
                      type="number"
                      value={config.index_config.top_n_retrieval}
                      onChange={(e) => updateIndexConfig('top_n_retrieval', parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      min="1"
                      max="50"
                    />
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="use-bm25"
                      checked={config.index_config.use_bm25}
                      onChange={(e) => updateIndexConfig('use_bm25', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="use-bm25" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Use BM25 (Hybrid Retrieval)
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="use-vector-db"
                      checked={config.index_config.use_vector_db}
                      onChange={(e) => updateIndexConfig('use_vector_db', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="use-vector-db" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Use Vector Database
                    </label>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-between items-center pt-6 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={handleApplyToAll}
                  disabled={applyToAllMutation.isPending || isApplyingToAll}
                  className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isApplyingToAll ? 'Applying to All...' : 'Apply to All Documents'}
                </button>

                <div className="flex space-x-3">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={updateConfigMutation.isPending}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {updateConfigMutation.isPending ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              Failed to load configuration
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}; 