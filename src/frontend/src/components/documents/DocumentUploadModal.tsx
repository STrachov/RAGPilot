"use client";

import React, { useState, useRef, useCallback } from 'react';
import { documentsService, UploadProgress } from '@/services/documents';
import { DocumentSourceType, Document } from '@/types/ragpilot';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (document: Document) => void;
  onUploadError?: (error: string) => void;
}

interface FileWithProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  document?: Document;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  onUploadError,
}) => {
  const [files, setFiles] = useState<FileWithProgress[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [runPipeline, setRunPipeline] = useState(true); // Default checked
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle file selection
  const handleFiles = useCallback((selectedFiles: FileList | File[]) => {
    const newFiles: FileWithProgress[] = [];
    
    Array.from(selectedFiles).forEach((file) => {
      const validation = documentsService.validateFile(file);
      
      if (validation.isValid) {
        newFiles.push({
          file,
          progress: 0,
          status: 'pending',
        });
      } else {
        newFiles.push({
          file,
          progress: 0,
          status: 'error',
          error: validation.error,
        });
      }
    });

    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  // Handle drag events
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      handleFiles(droppedFiles);
    }
  }, [handleFiles]);

  // Handle file input change
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  }, [handleFiles]);

  // Upload a single file
  const uploadFile = async (fileWithProgress: FileWithProgress, index: number) => {
    const onProgress = (progress: UploadProgress) => {
      setFiles(prev => prev.map((f, i) => 
        i === index 
          ? { ...f, progress: progress.percentage, status: 'uploading' as const }
          : f
      ));
    };

    try {
      // Determine source type based on file type
      const getSourceType = (file: File): DocumentSourceType => {
        const type = file.type.toLowerCase();

        if (type.includes('pdf')) {
          return DocumentSourceType.PDF;
        }
        if (type.includes('email') || type.includes('eml')) {
          return DocumentSourceType.EMAIL;
        }
        if (type.includes('report')) {
          return DocumentSourceType.REPORT;
        }
        if (type.includes('sharepoint')) {
          return DocumentSourceType.SHAREPOINT;
        }
        return DocumentSourceType.OTHER;
      };

      const uploadRequest = {
        file: fileWithProgress.file,
        source_type: getSourceType(fileWithProgress.file),
        run_pipeline: runPipeline, // Include pipeline option
      };

      console.log('Starting upload with pipeline option:', runPipeline);
      const document = await documentsService.uploadDocument(uploadRequest, onProgress);
      console.log('Upload completed successfully:', document);

      setFiles(prev => prev.map((f, i) => 
        i === index 
          ? { ...f, progress: 100, status: 'success' as const, document }
          : f
      ));

      onUploadSuccess(document);
    } catch (error) {
      console.error('Upload failed with error:', error);
      console.error('Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined,
        response: error && typeof error === 'object' && 'response' in error ? (error as any).response : undefined
      });
      
      let errorMessage = 'Upload failed';
      
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as any;
        errorMessage = axiosError.response?.data?.message || axiosError.message || 'Upload failed';
      }
      
      setFiles(prev => prev.map((f, i) => 
        i === index 
          ? { ...f, status: 'error' as const, error: errorMessage }
          : f
      ));

      if (onUploadError) {
        onUploadError(errorMessage);
      }
    }
  };

  // Upload all pending files
  const handleUploadAll = async () => {
    setIsUploading(true);
    
    const pendingFiles = files
      .map((file, index) => ({ file, index }))
      .filter(({ file }) => file.status === 'pending');

    try {
      await Promise.all(
        pendingFiles.map(({ file, index }) => uploadFile(file, index))
      );
    } finally {
      setIsUploading(false);
    }
  };

  // Remove file from list
  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Clear all files
  const clearFiles = () => {
    setFiles([]);
  };

  // Close modal and reset state
  const handleClose = () => {
    if (!isUploading) {
      setFiles([]);
      setRunPipeline(true); // Reset to default
      onClose();
    }
  };

  if (!isOpen) return null;

  const pendingFiles = files.filter(f => f.status === 'pending');
  const errorFiles = files.filter(f => f.status === 'error');
  const hasValidFiles = pendingFiles.length > 0;

  return (
    <div className="fixed inset-0 z-[99999] overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black/50 transition-opacity z-[99998]"
          onClick={handleClose}
        />

        {/* Modal */}
        <div className="relative inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full sm:p-6 z-[99999] max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Upload Documents
            </h3>
            <button
              onClick={handleClose}
              disabled={isUploading}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Pipeline Options */}
          <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-start space-x-3">
              <input
                id="run-pipeline"
                type="checkbox"
                checked={runPipeline}
                onChange={(e) => setRunPipeline(e.target.checked)}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <div className="flex-1">
                <label htmlFor="run-pipeline" className="text-sm font-medium text-gray-900 dark:text-white cursor-pointer">
                  Run subsequent pipeline operations
                </label>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Automatically process documents through parsing, chunking, and indexing stages after upload
                </p>
              </div>
            </div>
          </div>

          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragOver
                ? 'border-primary bg-primary/5'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div className="mt-4">
              <p className="text-lg font-medium text-gray-900 dark:text-white">
                Drop files here to upload
              </p>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                or{' '}
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="font-medium text-primary hover:text-primary/80"
                >
                  browse files
                </button>
              </p>
            </div>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              PDF, Word (DOCX), Text, Markdown, CSV, JSON up to 100MB
            </p>
          </div>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileInputChange}
            accept=".pdf,.doc,.docx,.txt,.md,.csv,.json,.xls,.xlsx,.epub"
            className="hidden"
          />

          {/* File list */}
          {files.length > 0 && (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                  Selected Files ({files.length})
                </h4>
                <button
                  onClick={clearFiles}
                  disabled={isUploading}
                  className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 disabled:opacity-50"
                >
                  Clear all
                </button>
              </div>

              <div className="space-y-3 max-h-64 overflow-y-auto">
                {files.map((fileWithProgress, index) => (
                  <div
                    key={`${fileWithProgress.file.name}-${index}`}
                    className="flex items-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                  >
                    <div className="flex-shrink-0 text-2xl mr-3">
                      {documentsService.getFileIcon(fileWithProgress.file)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {fileWithProgress.file.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {documentsService.formatFileSize(fileWithProgress.file.size)}
                      </p>
                      
                      {/* Progress bar */}
                      {fileWithProgress.status === 'uploading' && (
                        <div className="mt-2">
                          <div className="bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div
                              className="bg-primary h-2 rounded-full transition-all duration-300"
                              style={{ width: `${fileWithProgress.progress}%` }}
                            />
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {fileWithProgress.progress}%
                          </p>
                        </div>
                      )}
                      
                      {/* Error message */}
                      {fileWithProgress.status === 'error' && (
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                          {fileWithProgress.error}
                        </p>
                      )}
                    </div>

                    {/* Status icon */}
                    <div className="flex-shrink-0 ml-3">
                      {fileWithProgress.status === 'success' && (
                        <div className="w-6 h-6 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                          <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      )}
                      
                      {fileWithProgress.status === 'error' && (
                        <div className="w-6 h-6 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                          <svg className="w-4 h-4 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </div>
                      )}
                      
                      {fileWithProgress.status === 'pending' && (
                        <button
                          onClick={() => removeFile(index)}
                          disabled={isUploading}
                          className="w-6 h-6 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3 mt-6 pt-6 pb-2 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 sticky bottom-0 -mx-6 px-6">
            <button
              type="button"
              onClick={handleClose}
              disabled={isUploading}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              Cancel
            </button>
            
            <button
              type="button"
              onClick={handleUploadAll}
              disabled={!hasValidFiles || isUploading}
              className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? (
                <div className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {runPipeline ? 'Uploading & Processing...' : 'Uploading...'}
                </div>
              ) : hasValidFiles ? (
                `${runPipeline ? 'Upload & Process' : 'Upload Only'} ${pendingFiles.length} file${pendingFiles.length !== 1 ? 's' : ''}`
              ) : (
                'Select files to upload'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}; 