"use client";

import React, { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { useAuthStore } from "@/stores/authStore";
import { 
  Document, 
  Pipeline,
  ParseConfig,
  ChunkingConfig,
  IndexConfig
} from "@/types/ragpilot";

interface PipelineSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: Document;
  onPipelineStarted?: () => void;
}

export const PipelineSelectionModal: React.FC<PipelineSelectionModalProps> = ({
  isOpen,
  onClose,
  document,
  onPipelineStarted
}) => {
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [selectedPipeline, setSelectedPipeline] = useState<string>('');
  const { data: pipelines, isLoading: pipelinesLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => documentsService.getAvailablePipelines(),
    enabled: isOpen && isAuthenticated,
  });

  const executePipelineMutation = useMutation({
    mutationFn: (pipelineName: string) => documentsService.executePipeline(document.id, pipelineName),
    onSuccess: () => {
      if (onPipelineStarted) {
        onPipelineStarted();
      }
      onClose();
    },
  });

  const handleExecutePipeline = () => {
    if (selectedPipeline) {
      executePipelineMutation.mutate(selectedPipeline);
    }
  };

  const getDifficultyBadge = (pipeline: Pipeline) => {
    const colors = {
      easy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      hard: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    };
    const level = 'easy'; // Placeholder
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[level]}`}>
        {level.charAt(0).toUpperCase() + level.slice(1)}
      </span>
    );
  };

  const getEstimatedDuration = (pipeline: Pipeline) => {
    return `~5 min`; // Placeholder
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[99999] overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black/50 transition-opacity z-[99998]"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full sm:p-6 z-[99999] max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                  Select Processing Pipeline
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Choose how to process: {document.filename}
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Pipeline Selection */}
            {pipelinesLoading ? (
              <div className="animate-pulse space-y-3">
                <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
                <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
                <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
              </div>
            ) : (
              <div className="space-y-3 mb-6">
                {pipelines && Object.entries(pipelines).map(([name, pipeline]) => (
                  <div
                    key={name}
                    className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                      selectedPipeline === name
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                    }`}
                    onClick={() => setSelectedPipeline(name)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        <div
                          className={`w-4 h-4 rounded-full border-2 ${
                            selectedPipeline === name
                              ? 'border-blue-500 bg-blue-500'
                              : 'border-gray-300 dark:border-gray-600'
                          }`}
                        >
                          {selectedPipeline === name && (
                            <div className="w-2 h-2 bg-white rounded-full mx-auto mt-0.5"></div>
                          )}
                        </div>
                        <h4 className="font-medium text-gray-900 dark:text-white">
                          {pipeline.name}
                        </h4>
                      </div>
                      <div className="flex items-center space-x-2">
                        {getDifficultyBadge(pipeline)}
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {getEstimatedDuration(pipeline)}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                      {pipeline.description}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {pipeline.stages.map((stage, index) => (
                        <span
                          key={stage.name}
                          className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                        >
                          {index > 0 && <span className="mr-1">→</span>}
                          {stage.name}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Footer */}
            <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="button"
                onClick={handleExecutePipeline}
                disabled={executePipelineMutation.isPending}
                className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {executePipelineMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Starting Pipeline...
                  </>
                ) : (
                  'Start Pipeline'
                )}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>

            {/* Error Display */}
            {executePipelineMutation.isError && (
              <div className="mx-4 mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-700 dark:text-red-300">
                  Failed to start pipeline: {(executePipelineMutation.error as any)?.message || 'Unknown error'}
                </p>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}; 