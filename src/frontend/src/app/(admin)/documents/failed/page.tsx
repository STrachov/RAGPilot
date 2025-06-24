"use client";

import React, { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { Document, getOverallStatus } from "@/types/ragpilot";

export default function FailedDocumentsPage() {
  const queryClient = useQueryClient();

  useEffect(() => {
    document.title = "Failed Documents | RAGPilot";
  }, []);

  const { data: allDocuments, isLoading, error } = useQuery({
    queryKey: ['documents', 'failed'],
    queryFn: () => documentsService.getDocuments({ 
      limit: 100 
    }),
  });

  // Filter for failed documents on the client side
  const documents = allDocuments?.filter(doc => getOverallStatus(doc.status) === 'failed') || [];

  const retryMutation = useMutation({
    mutationFn: (documentId: string) => {
      // Note: retryProcessing method needs to be implemented in documentsService
      console.log('Retry processing for document:', documentId);
      return Promise.resolve({ success: true });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => documentsService.deleteDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

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

  const handleRetry = (documentId: string) => {
    retryMutation.mutate(documentId);
  };

  const handleDelete = (documentId: string) => {
    if (confirm('Are you sure you want to delete this failed document? This action cannot be undone.')) {
      deleteMutation.mutate(documentId);
    }
  };

  if (isLoading) {
    return (
      <div>
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Failed Documents
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Documents that failed to process with error details
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
            Failed Documents
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Documents that failed to process with error details
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
                Error loading failed documents
              </h3>
              <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                <p>Unable to fetch failed documents. Please try again later.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const failedDocs = documents || [];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Failed Documents
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Documents that failed to process with error details and retry options
        </p>
      </div>

      {/* Failed Status */}
      {failedDocs.length > 0 && (
        <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                {failedDocs.length} Document{failedDocs.length !== 1 ? 's' : ''} Failed to Process
              </h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                Review the errors below and retry processing or remove failed documents.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Documents List */}
      {failedDocs.length === 0 ? (
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
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            No failed documents
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Great! All your documents have been processed successfully.
          </p>
        </div>
      ) : (
                 <div className="space-y-4">
           {failedDocs.map((doc: Document) => (
             <div
               key={doc.id}
               className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-red-400"
             >
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                    <svg
                      className="w-6 h-6 text-red-600 dark:text-red-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.082 16.5c-.77.833.192 2.5 1.732 2.5z"
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
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                        Failed
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
                       Failed {getTimeAgo(doc.updated_at || doc.created_at)}
                     </span>
                   </div>
                   
                                     
                   {!!doc.metadata?.error && (
                     <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-md">
                       <div className="flex">
                         <div className="flex-shrink-0">
                           <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                             <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                           </svg>
                         </div>
                         <div className="ml-3">
                           <h4 className="text-sm font-medium text-red-800 dark:text-red-200">
                             Processing Error
                           </h4>
                           <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                             {String(doc.metadata.error)}
                           </p>
                         </div>
                       </div>
                     </div>
                   )}

                  {/* Action Buttons */}
                  <div className="mt-4 flex space-x-3">
                    <button
                      onClick={() => handleRetry(doc.id)}
                      disabled={retryMutation.isPending}
                      className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {retryMutation.isPending ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Retrying...
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          Retry Processing
                        </>
                      )}
                    </button>
                    
                    <button
                      onClick={() => handleDelete(doc.id)}
                      disabled={deleteMutation.isPending}
                      className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {deleteMutation.isPending ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400 mr-2"></div>
                          Deleting...
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Delete
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
} 