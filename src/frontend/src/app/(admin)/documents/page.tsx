"use client";

//import type { Metadata } from "next";
import React, { useState, useEffect, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { 
  DocumentStatusChart,
  RecentDocuments,
  QuickActions,
  GlobalConfigModal,
} from "@/components/ragpilot";
import { DocumentUploadModal } from "@/components/documents";
import { DocumentStagesControl } from "@/components/ragpilot/DocumentStagesControl";
import { Document, DocumentSourceType, SystemStats, getOverallStatus, getCurrentStageProgress, getStageDisplayName, getCurrentStageName, getCurrentStageStatus } from "@/types/ragpilot";
import { documentsService } from "@/services/documents";
import { adminService } from "@/services/admin";
import { useDocumentStatusPolling } from "@/hooks/useDocumentStatusPolling";



const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export default function DocumentsPage() {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isGlobalConfigModalOpen, setIsGlobalConfigModalOpen] = useState(false);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);

  const queryClient = useQueryClient();

  // Set page title
  useEffect(() => {
    document.title = "Documents | RAGPilot - Intelligent Document QA Platform";
  }, []);

  // Fetch system statistics
  const { data: systemStats, isLoading: statsLoading } = useQuery({
    queryKey: ['systemStats'],
    queryFn: () => adminService.getSystemStats(),
    //refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch documents with filtering
  const { data: documents, isLoading: documentsLoading, error: documentsError } = useQuery({
    queryKey: ['documents', selectedStatus, searchQuery],
    queryFn: () => documentsService.getDocuments({
      // Note: Backend still expects simple status for filtering
      limit: 100,
    }),
    // No refetchInterval - using dedicated polling hook instead
  });

  // Filter documents by search query and status
  const filteredDocuments = documents?.filter(doc => {
    const matchesSearch = doc.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.filename?.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (!matchesSearch) return false;
    
    if (selectedStatus === 'all') return true;
    
         // Map frontend filter to document status
     const overallStatus = getOverallStatus(doc.status);
     const currentStage = getCurrentStageName(doc.status);
     switch (selectedStatus) {
       case 'completed':
         return overallStatus === 'completed';
       case 'processing':
         return overallStatus === 'processing';
       case 'pending':
         return overallStatus === 'pending';
       case 'failed':
         return overallStatus === 'failed';
       case 'upload':
         return currentStage === 'upload';
       case 'parse':
         return currentStage === 'parse';
       case 'chunk':
         return currentStage === 'chunk';
       case 'index':
         return currentStage === 'index';
       default:
         return true;
     }
  }) || [];

  // Get document IDs for polling - use memoization to prevent infinite loops
  const currentPageDocumentIds = useMemo(() => {
    return filteredDocuments.map(doc => doc.id);
  }, [filteredDocuments.map(doc => doc.id).join(',')]);

  // Poll status for documents on current page with running parse stages
  const { data: updatedDocuments } = useDocumentStatusPolling(currentPageDocumentIds, {
    enabled: currentPageDocumentIds.length > 0,
  });

  // Update documents when polling returns new data
  useEffect(() => {
    if (updatedDocuments && updatedDocuments.length > 0) {
      queryClient.setQueryData(['documents', selectedStatus, searchQuery], (oldData: Document[] | undefined) => {
        if (!oldData) return oldData;
        
        // Create a map of updated documents for faster lookup
        const updatedDocsMap = new Map(updatedDocuments.map(doc => [doc.id, doc]));
        
        // Update existing documents with new status
        return oldData.map(doc => updatedDocsMap.get(doc.id) || doc);
      });
    }
  }, [updatedDocuments, queryClient, selectedStatus, searchQuery]);

  // Calculate document statistics using the new status structure
  const documentsByStatus = {
    total: documents?.length || 0,
    completed: documents?.filter(d => getOverallStatus(d.status) === 'completed').length || 0,
    processing: documents?.filter(d => getOverallStatus(d.status) === 'processing').length || 0,
    pending: documents?.filter(d => getOverallStatus(d.status) === 'pending').length || 0,
    failed: documents?.filter(d => getOverallStatus(d.status) === 'failed').length || 0,
  };

  const handleUploadSuccess = (document: Document) => {
    setNotification({
      type: 'success',
      message: `"${document.title || document.filename}" uploaded successfully`,
    });
    
    // Refresh documents and stats
    queryClient.invalidateQueries({ queryKey: ['documents'] });
    queryClient.invalidateQueries({ queryKey: ['systemStats'] });
    
    // Clear notification after 5 seconds
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };

  const handleUploadError = (error: string) => {
    setNotification({
      type: 'error',
      message: error,
    });
    
    // Clear notification after 5 seconds
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };

  const closeUploadModal = () => {
    setIsUploadModalOpen(false);
  };

  const handleDocumentSelect = (docId: string) => {
    setSelectedDocuments(prev => 
      prev.includes(docId) 
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const handleSelectAll = () => {
    if (selectedDocuments.length === filteredDocuments.length) {
      setSelectedDocuments([]);
    } else {
      setSelectedDocuments(filteredDocuments.map(doc => doc.id));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedDocuments.length === 0) return;
    
    try {
      const result = await documentsService.bulkDeleteDocuments(selectedDocuments);
      
      if (result.deleted.length > 0) {
        setNotification({
          type: 'success',
          message: `${result.deleted.length} documents deleted successfully${result.failed.length > 0 ? `, ${result.failed.length} failed` : ''}`,
        });
      } else {
        setNotification({
          type: 'error',
          message: 'Failed to delete any documents',
        });
      }
      
      setSelectedDocuments([]);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (error) {
      setNotification({
        type: 'error',
        message: 'Failed to delete selected documents',
      });
    }
  };

  const handleBulkReprocess = async () => {
    if (selectedDocuments.length === 0) return;
    
    try {
      // TODO: Implement bulk reprocess API call
      setNotification({
        type: 'success',
        message: `${selectedDocuments.length} documents queued for reprocessing`,
      });
      setSelectedDocuments([]);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (error) {
      setNotification({
        type: 'error',
        message: 'Failed to reprocess selected documents',
      });
    }
  };

  const handleBulkDownload = async () => {
    if (selectedDocuments.length === 0) return;
    
    try {
      // TODO: Implement bulk download API call
      setNotification({
        type: 'success',
        message: `Downloading ${selectedDocuments.length} documents`,
      });
    } catch (error) {
      setNotification({
        type: 'error',
        message: 'Failed to download selected documents',
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Notification */}
      {notification && (
        <div className={`p-4 rounded-md ${
          notification.type === 'success' 
            ? 'bg-green-50 text-green-800 border border-green-200' 
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          <div className="flex justify-between items-center">
            <span>{notification.message}</span>
            <button 
              onClick={() => setNotification(null)}
              className="text-gray-500 hover:text-gray-700"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Documents</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage and process your documents with AI-powered parsing and chunking
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setIsGlobalConfigModalOpen(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
          >
            <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Global Settings
          </button>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
          >
            <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Upload Document
          </button>
        </div>
      </div>

      {/* System Statistics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-blue-500"
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
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Total Documents
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {statsLoading ? 'Loading...' : (systemStats?.total_documents?.toLocaleString() || '0')}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-green-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Processed
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {documentsLoading ? 'Loading...' : documentsByStatus.completed.toLocaleString()}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-yellow-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Processing
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {documentsLoading ? 'Loading...' : documentsByStatus.processing.toLocaleString()}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-purple-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
                  />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Storage Used
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {statsLoading ? 'Loading...' : `${systemStats?.storage_used_mb?.toFixed(1) || '0'} MB`}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Filter Controls */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <div className="flex flex-col space-y-4 sm:flex-row sm:space-y-0 sm:space-x-4 sm:items-center sm:justify-between">
          {/* Search */}
          <div className="flex-1 max-w-lg">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-700 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 dark:focus:placeholder-gray-500 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Status Filter and Bulk Actions */}
          <div className="flex items-center space-x-4">
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
              <option value="upload">Upload</option>
              <option value="parse">Parse</option>
              <option value="chunk">Chunk</option>
              <option value="index">Index</option>
            </select>

            {selectedDocuments.length > 0 && (
              <div className="relative">
                <select
                  onChange={(e) => {
                    const action = e.target.value;
                    if (action === 'delete') handleBulkDelete();
                    else if (action === 'reprocess') handleBulkReprocess();
                    else if (action === 'download') handleBulkDownload();
                    e.target.value = ''; // Reset select
                  }}
                  className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  defaultValue=""
                >
                  <option value="" disabled>
                    Actions for {selectedDocuments.length} selected
                  </option>
                  <option value="download">Download Selected</option>
                  <option value="reprocess">Reprocess Selected</option>
                  <option value="delete">Delete Selected</option>
                </select>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
            Documents ({filteredDocuments.length})
          </h3>
        </div>

        {documentsLoading ? (
          <div className="p-6">
            <div className="animate-pulse space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-200 rounded dark:bg-gray-700"></div>
              ))}
            </div>
          </div>
        ) : documentsError ? (
          <div className="p-6 text-center text-red-500">
            Failed to load documents
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="p-6 text-center text-gray-500 dark:text-gray-400">
            {searchQuery ? 'No documents match your search' : 'No documents uploaded yet'}
          </div>
        ) : (
          <div className="space-y-4 p-6">
            {/* Select All Header */}
            <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={selectedDocuments.length === filteredDocuments.length && filteredDocuments.length > 0}
                  onChange={handleSelectAll}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Select all ({filteredDocuments.length})
                </span>
              </div>
              {selectedDocuments.length > 0 && (
                <span className="text-sm text-blue-600">
                  {selectedDocuments.length} selected
                </span>
              )}
            </div>
            
            {filteredDocuments.map((document) => (
              <div key={document.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
                {/* Document Header - Single Responsive Container */}
                <div className="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-4">
                  {/* Document info section */}
                  <div className="flex items-center space-x-4 flex-1">
                    <input
                      type="checkbox"
                      checked={selectedDocuments.includes(document.id)}
                      onChange={() => handleDocumentSelect(document.id)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    
                    <div className="flex items-center space-x-3 flex-1">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700">
                        <svg className="h-6 w-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {document.title || document.filename}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center space-x-2">
                          <span>{formatFileSize(document.file_size)}</span>
                          <span>•</span>
                          <span>{new Date(document.created_at).toLocaleDateString()}</span>
                          <span>•</span>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            getOverallStatus(document.status) === 'completed' 
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                              : getOverallStatus(document.status) === 'failed'
                              ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                              : getOverallStatus(document.status) === 'processing'
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                              : 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
                          }`}>
                            {getStageDisplayName(getCurrentStageName(document.status))} - {getCurrentStageStatus(document.status)}
                          </span>
                          <span className="text-xs text-gray-400">
                            {getCurrentStageProgress(document.status)}% complete
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions and Stage controls - responsive positioning */}
                  <div className="flex items-center space-x-3 justify-center sm:justify-end">
                    {/* Stage Control Buttons */}
                    <DocumentStagesControl 
                      document={document}
                      className=""
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={closeUploadModal}
        onUploadSuccess={handleUploadSuccess}
        onUploadError={handleUploadError}
      />

      {/* Global Configuration Modal */}
      <GlobalConfigModal
        isOpen={isGlobalConfigModalOpen}
        onClose={() => setIsGlobalConfigModalOpen(false)}
      />
    </div>
  );
} 