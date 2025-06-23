"use client";

import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { Document, DocumentStageInfo, getOverallStatus } from "@/types/ragpilot";
import { ParserSelectionModal } from "./ParserSelectionModal";
import { ParseResultsModal } from "./ParseResultsModal";

interface DocumentStagesControlProps {
  document: Document;
  className?: string;
  variant?: 'full' | 'compact';
}

const StageDropdown = ({
  stage,
  stageInfo,
  onAction,
  isLoading = false,
  size = 'small',
  document
}: {
  stage: string;
  stageInfo: DocumentStageInfo;
  onAction: (action: string) => void;
  isLoading?: boolean;
  size?: 'small' | 'large';
  document: Document;
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isParserModalOpen, setIsParserModalOpen] = useState(false);
  const [isParseResultsModalOpen, setIsParseResultsModalOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState<'down' | 'up'>('down');
  const buttonRef = React.useRef<HTMLButtonElement>(null);

  // Calculate dropdown position when opening
  const handleToggleDropdown = () => {
    if (!isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const spaceBelow = viewportHeight - rect.bottom;
      const dropdownHeight = 200; // Approximate dropdown height
      
      if (spaceBelow < dropdownHeight && rect.top > dropdownHeight) {
        setDropdownPosition('up');
      } else {
        setDropdownPosition('down');
      }
    }
    setIsOpen(!isOpen);
  };

  const getStatusColor = () => {
    switch (stageInfo?.status) {
      case "completed": return "text-green-600 dark:text-green-400";
      case "running": return "text-blue-600 dark:text-blue-400";
      case "failed": return "text-red-600 dark:text-red-400";
      case "waiting": return "text-gray-500 dark:text-gray-400";
      default: return "text-gray-500 dark:text-gray-400";
    }
  };

  const getStatusIcon = () => {
    switch (stageInfo?.status) {
      case "completed":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case "running":
        return (
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
        );
      case "failed":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      case "waiting":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const getStageCommands = () => {
    switch (stage) {
      case "upload":
        return [
          { id: "download", label: "Download", icon: "download" },
          { id: "delete", label: "Delete", icon: "delete", danger: true }
        ];
      case "parse":
        return [
          { id: "reparse", label: "Configure and Parse", icon: "settings" },
          { id: "update-status", label: "Update Status", icon: "refresh" },
          ...(stageInfo?.status === "completed" ? [{ id: "view-results", label: "View Parse Results", icon: "eye" }] : []),
          ...(stageInfo?.status === "failed" ? [{ id: "view-error", label: "View Error", icon: "error" }] : [])
        ];
      case "chunk-index":
        return [
          { id: "reprocess", label: "Chunk & Index", icon: "process" },
          ...(stageInfo?.status === "completed" ? [{ id: "view-metrics", label: "View Quality Metrics", icon: "chart" }] : []),
          ...(stageInfo?.status === "failed" ? [{ id: "view-error", label: "View Error", icon: "error" }] : [])
        ];
      default:
        return [];
    }
  };

  const handleCommand = (commandId: string) => {
    setIsOpen(false);
    
    if (commandId === "reparse") {
      setIsParserModalOpen(true);
    } else if (commandId === "view-results") {
      setIsParseResultsModalOpen(true);
    } else if (commandId === "update-status") {
      // Refresh document status
      onAction("refresh-status");
    } else {
      onAction(commandId);
    }
  };

  const getCommandIcon = (iconType: string) => {
    switch (iconType) {
      case "download":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      case "delete":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        );
      case "settings":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        );
      case "eye":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        );
      case "refresh":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        );
      case "chart":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        );
      case "error":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case "play":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5v14l11-7z" />
          </svg>
        );
      case "process":
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
        );
      default:
        return null;
    }
  };

  const commands = getStageCommands();
  const buttonSize = size === 'large' ? 'px-4 py-3 text-sm' : 'px-3 py-2 text-xs';
  const iconSize = size === 'large' ? 'h-5 w-5' : 'h-4 w-4';

  return (
    <div className="relative">
      {/* Stage Dropdown Button */}
      <button
        onClick={handleToggleDropdown}
        disabled={isLoading}
        className={`${buttonSize} ${getStatusColor()} border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2`}
        ref={buttonRef}
      >
        <div className={iconSize}>
          {getStatusIcon()}
        </div>
        <span className="font-medium">
          {stage === "chunk-index" ? "Chunk & Index" : stage.charAt(0).toUpperCase() + stage.slice(1)}
        </span>
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Menu */}
          <div className={`absolute left-0 w-56 rounded-md shadow-lg bg-white dark:bg-gray-700 ring-1 ring-black ring-opacity-5 z-[99999] ${
            dropdownPosition === 'up' ? 'bottom-full mb-2' : 'top-full mt-2'
          }`}>
            <div className="py-1" role="menu">
              {commands.map((command) => (
                <button
                  key={command.id}
                  onClick={() => handleCommand(command.id)}
                  className={`flex items-center w-full px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600 ${
                    command.danger 
                      ? 'text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20' 
                      : 'text-gray-700 dark:text-gray-200'
                  }`}
                  role="menuitem"
                >
                  <div className="mr-3 h-4 w-4">
                    {getCommandIcon(command.icon)}
                  </div>
                  {command.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Parser Selection Modal */}
      <ParserSelectionModal
        isOpen={isParserModalOpen}
        onClose={() => setIsParserModalOpen(false)}
        document={document}
      />

      {/* Parse Results Modal */}
      <ParseResultsModal
        isOpen={isParseResultsModalOpen}
        onClose={() => setIsParseResultsModalOpen(false)}
        document={document}
      />
    </div>
  );
};

const ErrorModal = ({
  isOpen,
  onClose,
  error,
  stage
}: {
  isOpen: boolean;
  onClose: () => void;
  error: any;
  stage: string;
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center" style={{ zIndex: 9999999, backgroundColor: 'rgba(0, 0, 0, 0.5)' }}>
      <div className="bg-white dark:bg-boxdark p-6 rounded-lg max-w-lg w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-black dark:text-white">
            {stage.charAt(0).toUpperCase() + stage.slice(1)} Stage Error
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>
        
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Error Message:</label>
            <div className="mt-1 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-red-800 dark:text-red-200 text-sm">
              {error?.error_message || "Unknown error occurred"}
            </div>
          </div>
          
          {error?.failed_at && (
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Failed At:</label>
              <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                {new Date(error.failed_at).toLocaleString()}
              </div>
            </div>
          )}
          
          {error?.attempts && error.attempts > 1 && (
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Attempts:</label>
              <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                {error.attempts}
              </div>
            </div>
          )}
        </div>
        
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary/90 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export const DocumentStagesControl: React.FC<DocumentStagesControlProps> = ({
  document,
  className = "",
  variant = 'compact'
}) => {
  const [errorModal, setErrorModal] = useState<{ isOpen: boolean; stage?: string; error?: any }>({
    isOpen: false
  });
  
  const queryClient = useQueryClient();

  // Mutation for starting stages
  const startStageMutation = useMutation({
    mutationFn: ({ stage }: { stage: 'parse' | 'chunk-index' }) => {
      console.log(`Starting ${stage} stage for document ${document.id}`);
      return documentsService.startDocumentStage(document.id, stage);
    },
    onSuccess: (data) => {
      console.log('Stage started successfully:', data);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (error: any) => {
      console.error('Failed to start stage:', error);
      alert(`Failed to start stage: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  // Mutation for reprocessing document (rechunk + reindex)
  const reprocessMutation = useMutation({
    mutationFn: () => documentsService.reprocessDocument(document.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      alert('Document reprocessing started successfully!');
    },
    onError: (error: any) => {
      console.error('Failed to reprocess document:', error);
      alert(`Failed to reprocess document: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  // Mutation for deleting document
  const deleteMutation = useMutation({
    mutationFn: () => documentsService.deleteDocument(document.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (error: any) => {
      console.error('Failed to delete document:', error);
      alert(`Failed to delete document: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  // Mutation for updating document status
  const updateStatusMutation = useMutation({
    mutationFn: () => documentsService.updateDocumentStatus(document.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document', document.id] });
    },
    onError: (error: any) => {
      console.error('Failed to update document status:', error);
      alert(`Failed to update document status: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  const handleStageAction = (stage: string, action: string) => {
    console.log(`Handling action: ${action} for stage: ${stage}`);
    
    switch (action) {
      case "download":
        handleDownload();
        break;
      case "delete":
        handleDelete();
        break;
      case "reprocess":
        handleReprocess();
        break;
      case "refresh-status":
        updateStatusMutation.mutate();
        break;
      case "view-error":
        const stageInfo = getStageInfo(stage);
        if (stageInfo) {
          setErrorModal({ isOpen: true, stage, error: stageInfo });
        }
        break;
      case "view-config":
        // TODO: Implement view parse config modal
        alert('View Parse Config - Coming soon!');
        break;
      case "view-metrics":
        // TODO: Implement view quality metrics modal
        alert('View Quality Metrics - Coming soon!');
        break;
      case "restart":
        handleRestart(stage);
        break;
      default:
        console.warn(`Unknown action: ${action}`);
    }
  };

  const getStageInfo = (stage: string): DocumentStageInfo | null => {
    if (!document.status || typeof document.status === 'string') return null;
    
    const stages = document.status.stages;
    
    switch (stage) {
      case "upload": return stages.upload;
      case "parse": return stages.parse;
      case "chunk-index": return stages["chunk-index"]; // Use the new combined stage
      default: return null;
    }
  };

  const handleDownload = async () => {
    try {
      const downloadUrl = await documentsService.getDocumentDownloadUrl(document.id);
      window.open(downloadUrl.download_url, '_blank');
    } catch (error: any) {
      console.error('Failed to get download URL:', error);
      alert(`Failed to download document: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  };

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete "${document.title || document.filename}"? This action cannot be undone.`)) {
      deleteMutation.mutate();
    }
  };

  const handleReprocess = () => {
    if (confirm(`Are you sure you want to reprocess "${document.title || document.filename}"? This will restart chunk and index stages with current global settings.`)) {
      reprocessMutation.mutate();
    }
  };

  const handleRestart = (stage: string) => {
    if (stage === "parse") {
      startStageMutation.mutate({ stage: 'parse' });
    } else if (stage === "chunk-index") {
      // For combined chunk-index stage
      startStageMutation.mutate({ stage: 'chunk-index' });
    }
  };

  if (!document || !document.status) {
    return (
      <div className={`text-center text-red-500 text-sm ${className}`}>
        No document data
      </div>
    );
  }

  // Handle old simple string status format
  if (typeof document.status === 'string') {
    return (
      <div className={`text-center text-gray-500 text-sm ${className}`}>
        Status: {document.status}
      </div>
    );
  }

  const stages = document.status.stages;

  if (variant === 'full') {
    return (
      <div className={className}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-black dark:text-white">
            Processing Stages
          </h3>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Overall Status: {getOverallStatus(document.status)}
          </div>
        </div>
        
        <div className="flex space-x-4 items-start">
          <StageDropdown
            stage="upload"
            stageInfo={stages.upload}
            onAction={(action) => handleStageAction("upload", action)}
            isLoading={startStageMutation.isPending || deleteMutation.isPending}
            size="large"
            document={document}
          />
          
          <StageDropdown
            stage="parse"
            stageInfo={stages.parse}
            onAction={(action) => handleStageAction("parse", action)}
            isLoading={startStageMutation.isPending}
            size="large"
            document={document}
          />
          
          <StageDropdown
            stage="chunk-index"
            stageInfo={stages["chunk-index"]}
            onAction={(action) => handleStageAction("chunk-index", action)}
            isLoading={startStageMutation.isPending || reprocessMutation.isPending}
            size="large"
            document={document}
          />
        </div>

        <ErrorModal
          isOpen={errorModal.isOpen}
          onClose={() => setErrorModal({ isOpen: false })}
          error={errorModal.error}
          stage={errorModal.stage || ''}
        />
      </div>
    );
  }

  // Compact variant (default for document rows)
  return (
    <div className={className}>
      <div className="flex items-center space-x-3">
        <StageDropdown
          stage="upload"
          stageInfo={stages.upload}
          onAction={(action) => handleStageAction("upload", action)}
          isLoading={startStageMutation.isPending || deleteMutation.isPending}
          document={document}
        />
        
        <StageDropdown
          stage="parse"
          stageInfo={stages.parse}
          onAction={(action) => handleStageAction("parse", action)}
          isLoading={startStageMutation.isPending}
          document={document}
        />
        
        <StageDropdown
          stage="chunk-index"
          stageInfo={stages["chunk-index"]}
          onAction={(action) => handleStageAction("chunk-index", action)}
          isLoading={startStageMutation.isPending || reprocessMutation.isPending}
          document={document}
        />
      </div>

      <ErrorModal
        isOpen={errorModal.isOpen}
        onClose={() => setErrorModal({ isOpen: false })}
        error={errorModal.error}
        stage={errorModal.stage || ''}
      />
    </div>
  );
}; 