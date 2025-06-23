"use client";

import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { Document } from "@/types/ragpilot";
import { ParserSelectionModal } from "./ParserSelectionModal";

interface DocumentActionsDropdownProps {
  document: Document;
  className?: string;
}

export const DocumentActionsDropdown: React.FC<DocumentActionsDropdownProps> = ({
  document,
  className = ""
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isParserModalOpen, setIsParserModalOpen] = useState(false);
  const queryClient = useQueryClient();

  // Mutation for reprocessing document
  const reprocessMutation = useMutation({
    mutationFn: () => documentsService.reprocessDocument(document.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setIsOpen(false);
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
      setIsOpen(false);
    },
    onError: (error: any) => {
      console.error('Failed to delete document:', error);
      alert(`Failed to delete document: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  const handleDownload = async () => {
    try {
      const downloadUrl = await documentsService.getDocumentDownloadUrl(document.id);
      window.open(downloadUrl.download_url, '_blank');
      setIsOpen(false);
    } catch (error: any) {
      console.error('Failed to get download URL:', error);
      alert(`Failed to download document: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  };

  const handleReprocess = () => {
    if (confirm(`Are you sure you want to reprocess "${document.title || document.filename}"? This will restart chunk and index stages with current global settings.`)) {
      reprocessMutation.mutate();
    }
  };

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete "${document.title || document.filename}"? This action cannot be undone.`)) {
      deleteMutation.mutate();
    }
  };

  const handleParserSelection = () => {
    setIsParserModalOpen(true);
    setIsOpen(false);
  };

  // Check if document can be reprocessed (parse stage must be completed)
  const canReprocess = document.status && 
    typeof document.status !== 'string' && 
    document.status.stages?.parse?.status === 'completed';

  return (
    <div className={`relative ${className}`}>
      {/* Dropdown Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
      >
        <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
        </svg>
        Actions
        <svg className="ml-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          <div className="absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white dark:bg-gray-700 ring-1 ring-black ring-opacity-5 z-[99999]">
            <div className="py-1" role="menu">
              {/* Download */}
              <button
                onClick={handleDownload}
                className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
                role="menuitem"
              >
                <svg className="mr-3 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download
              </button>

              {/* Reconfigure and Reparse */}
              <button
                onClick={handleParserSelection}
                className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
                role="menuitem"
              >
                <svg className="mr-3 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Reconfigure and Reparse
              </button>

              {/* Reprocess with Global Settings */}
              {canReprocess && (
                <button
                  onClick={handleReprocess}
                  disabled={reprocessMutation.isPending}
                  className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  role="menuitem"
                >
                  <svg className="mr-3 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  {reprocessMutation.isPending ? 'Reprocessing...' : 'Reprocess with Global Settings'}
                </button>
              )}

              <div className="border-t border-gray-100 dark:border-gray-600 my-1" />

              {/* Delete */}
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="flex items-center w-full px-4 py-2 text-sm text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
                role="menuitem"
              >
                <svg className="mr-3 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
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
    </div>
  );
}; 