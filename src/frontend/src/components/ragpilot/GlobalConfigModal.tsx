"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { configService } from "@/services/config";
import { documentsService } from "@/services/documents";
import { GlobalConfig, ParseConfig, ChunkingConfig, IndexConfig, ChunkingStrategy, IndexType, Pipeline, PipelineInfo } from "@/types/ragpilot";

interface GlobalConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const GlobalConfigModal: React.FC<GlobalConfigModalProps> = ({
  isOpen,
  onClose
}) => {
  const [config, setConfig] = useState<GlobalConfig | null>(null);
  const queryClient = useQueryClient();

  // Fetch current global configuration
  const { data: globalConfig, isLoading: isLoadingConfig } = useQuery({
    queryKey: ['globalConfig'],
    queryFn: () => configService.getGlobalConfig(),
    enabled: isOpen,
  });

  // Fetch available pipelines
  const { data: availablePipelines, isLoading: isLoadingPipelines } = useQuery({
    queryKey: ['availablePipelines'],
    queryFn: () => documentsService.getAvailablePipelines(),
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
      onClose();
    },
    onError: (error: any) => {
      console.error('Failed to update global configuration:', error);
      alert(`Failed to update configuration: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  const handleSave = () => {
    if (!config) return;
    updateConfigMutation.mutate(config);
  };
  
  const updateConfigField = (field: keyof GlobalConfig, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      [field]: value
    });
  };

  const updateParseConfig = (field: keyof ParseConfig, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      parse_config: {
        ...config.parse_config,
        [field]: value
      }
    });
  };

  const updateChunkConfig = (field: keyof ChunkingConfig, value: any) => {
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

  const isLoading = isLoadingConfig || isLoadingPipelines;

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
              {/* Pipeline Configuration */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Pipeline Configuration
                </h3>
                <div className="space-y-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Default Pipeline for Uploads
                  </label>
                  <div className="space-y-3">
                    {availablePipelines && Object.values(availablePipelines).map((pipeline: PipelineInfo) => (
                      <div key={pipeline.name} className="flex items-start p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <input
                          id={`pipeline-${pipeline.name}`}
                          type="radio"
                          name="default_pipeline"
                          value={pipeline.name}
                          checked={config.default_pipeline_name === pipeline.name}
                          onChange={(e) => updateConfigField('default_pipeline_name', e.target.value)}
                          className="h-4 w-4 mt-1 text-blue-600 focus:ring-blue-500 border-gray-300"
                        />
                        <div className="ml-3 text-sm">
                          <label htmlFor={`pipeline-${pipeline.name}`} className="font-medium text-gray-900 dark:text-white">
                            {pipeline.name}
                          </label>
                          <p className="text-gray-500 dark:text-gray-400">
                            {pipeline.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Parse Configuration */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Parse Configuration
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Parser Type
                    </label>
                    <select
                      value={config.parse_config.parser_type}
                      onChange={(e) => updateParseConfig('parser_type', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="docling">Docling</option>
                      <option value="marker">Marker</option>
                      <option value="unstructured">Unstructured</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      OCR Language
                    </label>
                    <select
                      value={config.parse_config.ocr_language}
                      onChange={(e) => updateParseConfig('ocr_language', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="auto">Auto</option>
                      <option value="en">English</option>
                      <option value="es">Spanish</option>
                      <option value="fr">French</option>
                      <option value="de">German</option>
                      <option value="it">Italian</option>
                      <option value="pt">Portuguese</option>
                      <option value="ru">Russian</option>
                      <option value="zh">Chinese</option>
                      <option value="ja">Japanese</option>
                      <option value="ko">Korean</option>
                    </select>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="do-ocr"
                      checked={config.parse_config.do_ocr}
                      onChange={(e) => updateParseConfig('do_ocr', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="do-ocr" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Enable OCR
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="extract-tables"
                      checked={config.parse_config.extract_tables}
                      onChange={(e) => updateParseConfig('extract_tables', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="extract-tables" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Extract Tables
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="extract-images"
                      checked={config.parse_config.extract_images}
                      onChange={(e) => updateParseConfig('extract_images', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="extract-images" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Extract Images
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="preserve-formatting"
                      checked={config.parse_config.preserve_formatting}
                      onChange={(e) => updateParseConfig('preserve_formatting', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="preserve-formatting" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Preserve Formatting
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="handle-multi-column"
                      checked={config.parse_config.handle_multi_column}
                      onChange={(e) => updateParseConfig('handle_multi_column', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="handle-multi-column" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Handle Multi-Column Layout
                    </label>
                  </div>
                </div>
              </div>

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
                      onChange={(e) => updateChunkConfig('strategy', e.target.value as ChunkingStrategy)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value={ChunkingStrategy.FIXED_SIZE}>Fixed Size</option>
                      <option value={ChunkingStrategy.SENTENCE}>Sentence</option>
                      <option value={ChunkingStrategy.PARAGRAPH}>Paragraph</option>
                      <option value={ChunkingStrategy.RECURSIVE}>Recursive</option>
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
                      id="preserve-table-structure"
                      checked={config.chunk_config.preserve_table_structure}
                      onChange={(e) => updateChunkConfig('preserve_table_structure', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="preserve-table-structure" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Preserve Table Structure
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="serialize-tables"
                      checked={config.chunk_config.serialize_tables}
                      onChange={(e) => updateChunkConfig('serialize_tables', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="serialize-tables" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Serialize Tables
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
                      <option value="sentence-transformers/all-MiniLM-L6-v2">all-MiniLM-L6-v2</option>
                      <option value="sentence-transformers/all-mpnet-base-v2">all-mpnet-base-v2</option>
                      <option value="text-embedding-3-small">OpenAI text-embedding-3-small</option>
                      <option value="text-embedding-3-large">OpenAI text-embedding-3-large</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Index Type
                    </label>
                    <select
                      value={config.index_config.index_type}
                      onChange={(e) => updateIndexConfig('index_type', e.target.value as IndexType)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value={IndexType.FAISS}>FAISS</option>
                      <option value={IndexType.QDRANT}>Qdrant</option>
                      <option value={IndexType.ELASTICSEARCH}>Elasticsearch</option>
                      <option value={IndexType.PINECONE}>Pinecone</option>
                      <option value={IndexType.WEAVIATE}>Weaviate</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Dimensions
                    </label>
                    <input
                      type="number"
                      value={config.index_config.dimensions}
                      onChange={(e) => updateIndexConfig('dimensions', parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      min="128"
                      max="4096"
                    />
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
                      id="use-vector-db"
                      checked={config.index_config.use_vector_db}
                      onChange={(e) => updateIndexConfig('use_vector_db', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="use-vector-db" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Use Vector Database
                    </label>
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
                      Use BM25 (Hybrid Search)
                    </label>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end pt-6 border-t border-gray-200 dark:border-gray-700">
                <div className="flex space-x-3">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-700 dark:text-gray-200 rounded-md font-medium transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={updateConfigMutation.isPending}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-md font-medium transition-colors"
                  >
                    {updateConfigMutation.isPending ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex justify-center py-8">
              <p className="text-gray-500 dark:text-gray-400">Failed to load configuration</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return typeof window !== 'undefined' ? createPortal(modalContent, document.body) : null;
}; 