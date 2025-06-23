"use client";

import React, { useEffect, useState } from "react";
import { DocumentUploadModal } from "@/components/documents";
import { Document } from "@/types/ragpilot";

export default function DocumentUploadPage() {
  const [notification, setNotification] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  useEffect(() => {
    document.title = "Upload Documents | RAGPilot";
  }, []);

  const handleUploadSuccess = (document: Document) => {
    setNotification({
      type: 'success',
      message: `"${document.title || document.filename}" uploaded successfully`,
    });
    
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

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Upload Documents
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Add new documents to your knowledge base for AI-powered Q&A
        </p>
      </div>

      {/* Notification */}
      {notification && (
        <div className={`mb-6 p-4 rounded-md ${
          notification.type === 'success' 
            ? 'bg-green-50 text-green-800 border border-green-200' 
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className={`h-5 w-5 ${
                  notification.type === 'success' ? 'text-green-400' : 'text-red-400'
                }`}
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                {notification.type === 'success' ? (
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                ) : (
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                )}
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium">{notification.message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Upload Interface */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <div className="text-center">
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
          <h3 className="mt-2 text-lg font-medium text-gray-900 dark:text-white">
            Document Upload
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Drag and drop files here or click the button below to upload documents
          </p>
          
          {/* Coming Soon Notice */}
          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-blue-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  Dedicated Upload Interface Coming Soon
                </h4>
                <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                  For now, you can upload documents using the upload button on the main Documents page or from the Dashboard.
                </p>
              </div>
            </div>
          </div>

          {/* Supported Formats */}
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              Supported Formats
            </h4>
            <div className="flex flex-wrap justify-center gap-2">
              {['PDF', 'DOCX', 'TXT', 'MD', 'CSV', 'JSON', 'XLSX', 'EPUB'].map((format) => (
                <span
                  key={format}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
                >
                  {format}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 