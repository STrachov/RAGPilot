"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { DocumentStatus, Document } from "@/types/ragpilot";
import { DocumentStagesControl } from "./DocumentStagesControl";



const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const RecentDocuments = () => {
  const { data: documents, isLoading, error } = useQuery({
    queryKey: ['recentDocuments'],
    queryFn: () => documentsService.getDocuments({ limit: 5 }), // Reduced to 5 since we'll show more detailed info
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) {
    return (
      <div className="rounded-sm border border-stroke bg-white p-6 shadow-default dark:border-strokedark dark:bg-boxdark">
        <div className="mb-6">
          <h4 className="text-xl font-semibold text-black dark:text-white">
            Recent Documents
          </h4>
        </div>
        <div className="animate-pulse space-y-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-3">
              <div className="h-4 bg-gray-200 rounded dark:bg-gray-700 w-3/4"></div>
              <div className="h-20 bg-gray-200 rounded dark:bg-gray-700"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-sm border border-stroke bg-white p-6 shadow-default dark:border-strokedark dark:bg-boxdark">
        <div className="mb-6">
          <h4 className="text-xl font-semibold text-black dark:text-white">
            Recent Documents
          </h4>
        </div>
        <div className="text-center text-red-500">
          Failed to load recent documents
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-sm border border-stroke bg-white p-6 shadow-default dark:border-strokedark dark:bg-boxdark">
      <div className="mb-6 flex items-center justify-between">
        <h4 className="text-xl font-semibold text-black dark:text-white">
          Recent Documents
        </h4>
        <button className="text-sm text-primary hover:underline">
          View All
        </button>
      </div>

      {!documents || documents.length === 0 ? (
        <div className="text-center text-meta-3 py-8">
          No documents uploaded yet
        </div>
      ) : (
        <div className="space-y-6">
          {documents.map((document: Document) => (
            <div
              key={document.id}
              className="border border-stroke rounded-lg p-4 dark:border-strokedark"
            >
              {/* Document Header - Single Responsive Container */}
              <div className="flex flex-col sm:flex-row sm:items-center space-y-3 sm:space-y-0 sm:space-x-4">
                {/* Document info */}
                <div className="flex items-center space-x-3 flex-1">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-meta-2 dark:bg-meta-4">
                    <svg className="h-5 w-5 text-meta-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-black dark:text-white">
                      {document.title}
                    </p>
                    <p className="text-xs text-meta-3">
                      {formatFileSize(document.file_size)} • {new Date(document.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                
                {/* Stage-Based Processing Controls */}
                <div className="flex justify-center sm:justify-end">
                  <DocumentStagesControl 
                    documentId={document.id}
                    className=""
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}; 