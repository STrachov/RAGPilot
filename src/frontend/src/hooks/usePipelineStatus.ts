import React from "react";
import { useQuery } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { PipelineStatus } from "@/types/ragpilot";

interface UsePipelineStatusOptions {
  documentId: string;
  pipelineName: string;
  enabled?: boolean;
  refetchInterval?: number;
  onStatusChange?: (status: PipelineStatus) => void;
}

export const usePipelineStatus = ({
  documentId,
  pipelineName,
  enabled = true,
  refetchInterval = 3000, // Poll every 3 seconds by default
  onStatusChange
}: UsePipelineStatusOptions) => {
  const {
    data: pipelineStatus,
    isLoading,
    isError,
    error,
    refetch
  } = useQuery({
    queryKey: ['pipeline-status', documentId, pipelineName],
    queryFn: () => documentsService.getPipelineStatus(documentId, pipelineName),
    enabled: enabled && !!documentId && !!pipelineName,
    refetchInterval: refetchInterval,
    refetchIntervalInBackground: true,
    staleTime: 0, // Always consider data stale to ensure fresh status
  });

  // Call status change callback when status updates
  React.useEffect(() => {
    if (pipelineStatus && onStatusChange) {
      onStatusChange(pipelineStatus);
    }
  }, [pipelineStatus, onStatusChange]);

  // Helper functions
  const isRunning = pipelineStatus?.overall_status === 'running';
  const isCompleted = pipelineStatus?.overall_status === 'completed';
  const isFailed = pipelineStatus?.overall_status === 'failed';
  const isPending = pipelineStatus?.overall_status === 'pending';
  
  const currentStage = pipelineStatus ? 
    Object.keys(pipelineStatus.stages).find(stageName => 
      pipelineStatus.stages[stageName].status === 'running'
    ) : undefined;
  
  const completedStages = pipelineStatus ? 
    Object.keys(pipelineStatus.stages).filter(stageName => 
      pipelineStatus.stages[stageName].status === 'completed'
    ) : [];
  
  const failedStages = pipelineStatus ? 
    Object.keys(pipelineStatus.stages).filter(stageName => 
      pipelineStatus.stages[stageName].status === 'failed'
    ) : [];

  return {
    pipelineStatus,
    isLoading,
    isError,
    error,
    refetch,
    
    // Status helpers
    isRunning,
    isCompleted,
    isFailed,
    isPending,
    
    // Stage helpers
    currentStage,
    completedStages,
    failedStages,
    
    // Progress information
    progress: pipelineStatus?.progress || 0,
    stageCount: pipelineStatus ? Object.keys(pipelineStatus.stages).length : 0,
    completedCount: completedStages.length,
    
    // Estimated time remaining (simple calculation)
    estimatedTimeRemaining: (() => {
      if (!pipelineStatus || !isRunning) return undefined;
      
      const totalStages = Object.keys(pipelineStatus.stages).length;
      const completed = completedStages.length;
      
      if (completed === 0) return undefined;
      
      // Simple estimation: assume each stage takes similar time
      // This could be improved with actual stage duration data
      const avgTimePerStage = 5; // minutes
      const remainingStages = totalStages - completed;
      
      return remainingStages * avgTimePerStage;
    })()
  };
};

// Hook for monitoring multiple pipeline statuses
export const useMultiplePipelineStatus = (
  pipelines: Array<{ documentId: string; pipelineName: string }>
) => {
  const queries = pipelines.map(({ documentId, pipelineName }) => 
    usePipelineStatus({ documentId, pipelineName })
  );
  
  const allRunning = queries.some(q => q.isRunning);
  const allCompleted = queries.every(q => q.isCompleted);
  const anyFailed = queries.some(q => q.isFailed);
  
  return {
    queries,
    allRunning,
    allCompleted,
    anyFailed,
    overallProgress: queries.reduce((sum, q) => sum + q.progress, 0) / queries.length
  };
}; 