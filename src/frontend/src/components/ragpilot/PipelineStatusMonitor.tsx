"use client";

import React from "react";
import { usePipelineStatus } from "@/hooks/usePipelineStatus";
import { PipelineStageStatus } from "@/types/ragpilot";

interface PipelineStatusMonitorProps {
  documentId: string;
  pipelineName: string;
  showDetailed?: boolean;
  className?: string;
}

export const PipelineStatusMonitor: React.FC<PipelineStatusMonitorProps> = ({
  documentId,
  pipelineName,
  showDetailed = false,
  className = ""
}) => {
  const {
    pipelineStatus,
    isLoading,
    isError,
    error,
    isRunning,
    isCompleted,
    isFailed,
    currentStage,
    progress,
    estimatedTimeRemaining
  } = usePipelineStatus({
    documentId,
    pipelineName,
    enabled: true,
    refetchInterval: 2000, // Poll every 2 seconds
    onStatusChange: (status) => {
      console.log(`Pipeline ${pipelineName} status updated:`, status);
    }
  });

  if (isLoading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-2"></div>
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className={`text-red-600 dark:text-red-400 text-sm ${className}`}>
        Error loading pipeline status: {(error as any)?.message}
      </div>
    );
  }

  if (!pipelineStatus) {
    return (
      <div className={`text-gray-500 dark:text-gray-400 text-sm ${className}`}>
        No pipeline status available
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 dark:text-green-400';
      case 'running': return 'text-blue-600 dark:text-blue-400';
      case 'failed': return 'text-red-600 dark:text-red-400';
      case 'pending': return 'text-yellow-600 dark:text-yellow-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'running':
        return (
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
        );
      case 'failed':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      case 'pending':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const getStageStatusColor = (status: PipelineStageStatus) => {
    switch (status) {
      case PipelineStageStatus.COMPLETED: return 'bg-green-500';
      case PipelineStageStatus.RUNNING: return 'bg-blue-500 animate-pulse';
      case PipelineStageStatus.FAILED: return 'bg-red-500';
      case PipelineStageStatus.WAITING: return 'bg-gray-300 dark:bg-gray-600';
      case PipelineStageStatus.SKIPPED: return 'bg-yellow-500';
      default: return 'bg-gray-300 dark:bg-gray-600';
    }
  };

  const formatTimeRemaining = (minutes?: number) => {
    if (!minutes) return '';
    if (minutes < 60) return `~${Math.round(minutes)}m remaining`;
    return `~${Math.round(minutes / 60)}h remaining`;
  };

  return (
    <div className={className}>
      {/* Overall Status */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className={getStatusColor(pipelineStatus.overall_status)}>
            {getStatusIcon(pipelineStatus.overall_status)}
          </span>
          <span className="font-medium text-gray-900 dark:text-white">
            {pipelineName.replace('_', ' ').toUpperCase()} Pipeline
          </span>
          <span className={`text-sm ${getStatusColor(pipelineStatus.overall_status)}`}>
            {pipelineStatus.overall_status.toUpperCase()}
          </span>
        </div>
        
        {isRunning && estimatedTimeRemaining && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formatTimeRemaining(estimatedTimeRemaining)}
          </span>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              isFailed ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-blue-500'
            }`}
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      {/* Current Stage */}
      {isRunning && currentStage && (
        <div className="mb-3 text-sm text-gray-600 dark:text-gray-400">
          Currently processing: <span className="font-medium text-blue-600 dark:text-blue-400">{currentStage}</span>
        </div>
      )}

      {/* Detailed Stage View */}
      {showDetailed && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Stage Details
          </h4>
          {Object.entries(pipelineStatus.stages).map(([stageName, stageInfo]) => (
            <div key={stageName} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${getStageStatusColor(stageInfo.status as PipelineStageStatus)}`}></div>
                <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                  {stageName}
                </span>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  stageInfo.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                  stageInfo.status === 'running' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                  stageInfo.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                  'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                }`}>
                  {stageInfo.status}
                </span>
              </div>
              
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {stageInfo.started_at && (
                  <div>Started: {new Date(stageInfo.started_at).toLocaleTimeString()}</div>
                )}
                {stageInfo.completed_at && (
                  <div>Completed: {new Date(stageInfo.completed_at).toLocaleTimeString()}</div>
                )}
                {stageInfo.failed_at && (
                  <div>Failed: {new Date(stageInfo.failed_at).toLocaleTimeString()}</div>
                )}
                {stageInfo.attempts && stageInfo.attempts > 1 && (
                  <div>Attempts: {stageInfo.attempts}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error Display */}
      {isFailed && (
        <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="text-sm text-red-700 dark:text-red-300">
            Pipeline execution failed. Check individual stage errors for details.
          </div>
        </div>
      )}

      {/* Success Display */}
      {isCompleted && (
        <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="text-sm text-green-700 dark:text-green-300">
            Pipeline completed successfully! All stages have finished processing.
          </div>
        </div>
      )}
    </div>
  );
}; 