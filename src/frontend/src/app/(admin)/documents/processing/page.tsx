"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { Document, DocumentStatusStructure, getOverallStatus } from "@/types/ragpilot";
import { useDocumentStatusPolling } from "@/hooks/useDocumentStatusPolling";

export default function ProcessingDocumentsPage() {
  const queryClient = useQueryClient();

  useEffect(() => {
    document.title = "Processing Documents | RAGPilot";
  }, []);

  // Fetch all documents and filter for processing ones
  const { data: allDocuments, isLoading, error } = useQuery({
    queryKey: ['documents', 'processing'],
    queryFn: () => documentsService.getDocuments({ limit: 100 }),
  });

  // Filter processing documents
  const documents = allDocuments?.filter(doc => getOverallStatus(doc.status) === 'processing') || [];

  // Get document IDs for polling - use memoization to prevent infinite loops
  const processingDocumentIds = useMemo(() => {
    return documents.map(doc => doc.id);
  }, [documents.map(doc => doc.id).join(',')]);

  // Poll status for processing documents only
  const { data: updatedDocuments } = useDocumentStatusPolling(processingDocumentIds, {
    enabled: processingDocumentIds.length > 0,
  });

  // Update documents when polling returns new data
  useEffect(() => {
    if (updatedDocuments && updatedDocuments.length > 0) {
      queryClient.setQueryData(['documents', 'processing'], (oldData: Document[] | undefined) => {
        if (!oldData) return oldData;
        
        // Create a map of updated documents for faster lookup
        const updatedDocsMap = new Map(updatedDocuments.map(doc => [doc.id, doc]));
        
        // Update existing documents with new status
        return oldData.map(doc => updatedDocsMap.get(doc.id) || doc);
      });
    }
  }, [updatedDocuments, queryClient]);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getTimeAgo = (date: string) => {
    const now = new Date();
    const uploadDate = new Date(date);
    const diffInMinutes = Math.floor((now.getTime() - uploadDate.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes} min ago`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
  };

  if (isLoading) {
    return (
      <div>
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Processing Documents
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Documents currently being processed and indexed
          </p>
        </div>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-2"></div>
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Processing Documents
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Documents currently being processed and indexed
          </p>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                Error loading processing documents
              </h3>
              <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                <p>Unable to fetch processing documents. Please try again later.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const processingDocs = documents;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Processing Documents
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Documents currently being processed and indexed
        </p>
      </div>

      {/* Processing Status */}
      <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
              {processingDocs.length} Document{processingDocs.length !== 1 ? 's' : ''} Processing
            </h3>
            <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
              Processing includes text extraction, chunking, embedding generation, and indexing.
            </p>
          </div>
        </div>
      </div>

      {/* Documents List */}
      {processingDocs.length === 0 ? (
        <div className="text-center py-12">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            No documents processing
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            All documents have been successfully processed or are in queue.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {processingDocs.map((doc: Document) => (
            <div
              key={doc.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6"
            >
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                    <svg
                      className="w-6 h-6 text-blue-600 dark:text-blue-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                      {doc.title || doc.filename}
                    </h3>
                    <div className="ml-4 flex-shrink-0">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                        <div className="animate-spin rounded-full h-3 w-3 border-b border-blue-600 mr-1"></div>
                        Processing
                      </span>
                    </div>
                  </div>
                  
                  <div className="mt-2 flex items-center text-sm text-gray-500 dark:text-gray-400 space-x-4">
                    <span>
                      {formatFileSize(doc.file_size || 0)}
                    </span>
                    <span>•</span>
                    <span>
                      {doc.content_type?.toUpperCase() || 'Unknown'}
                    </span>
                    <span>•</span>
                    <span>
                      Started {getTimeAgo(doc.created_at)}
                    </span>
                  </div>
                  
                  {!!doc.metadata?.error && (
                    <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
                      <div className="flex">
                        <div className="flex-shrink-0">
                          <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                        </div>
                        <div className="ml-3">
                          <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                            Processing Warning
                          </h4>
                          <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
                            {String(doc.metadata.error)}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
} 