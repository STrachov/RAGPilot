"use client";

import React, { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { Document } from "@/types/ragpilot";

interface ParseResultsModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: Document;
}

interface ParseResult {
  document_id: string;
  parse_result: any;
  status: string;
  completed_at?: string;
  parser_type: string;
}

export const ParseResultsModal: React.FC<ParseResultsModalProps> = ({
  isOpen,
  onClose,
  document
}) => {
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchParseResults = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // First try to get from document status if available
      if (typeof document.status === 'object' && document.status.stages?.parse) {
        const parseStage = document.status.stages.parse as any;
        
        if (parseStage.status === 'completed') {
          // Get result_key and table_keys from document.metadata
          const resultKey = document.metadata?.result_key;
          const tableKeys = document.metadata?.table_keys;
          
          // Always use the data from document status for completed documents
          const mockResult: ParseResult = {
            document_id: document.id,
            status: parseStage.status,
            completed_at: parseStage.completed_at,
            parser_type: parseStage.config?.parser_type || 'unknown',
            parse_result: {
              files: resultKey ? {
                main_result: resultKey
              } : {},
              tables: (tableKeys && Array.isArray(tableKeys)) ? tableKeys.map((key: string, index: number) => ({
                csv: key,
                markdown: `Table ${index + 1} data (download CSV for full data)`
              })) : [],
              metadata: {
                result_key: resultKey,
                table_keys: tableKeys,
                progress: document.metadata?.ragparser_progress,
                ragparser_task_id: document.metadata?.ragparser_task_id,
                source: 'document_status'
              }
            }
          };
          
          setParseResult(mockResult);
          setIsLoading(false);
          return;
        }
      }
      
      // Only try API call for non-completed documents or as last resort
      try {
      const result = await documentsService.getParseResults(document.id);
      setParseResult(result);
      } catch (apiError: any) {
        // If API fails and we have a completed parse stage, show a helpful message
        if (typeof document.status === 'object' && document.status.stages?.parse?.status === 'completed') {
          setError('Parse results are being processed. Please wait a moment and try again.');
        } else {
          throw apiError; // Re-throw if it's not a completed document
        }
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to fetch parse results');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchParseResults();
    }
  }, [isOpen, document.id]);

  const renderFileLinks = (files: any) => {
    if (!files || typeof files !== 'object') return null;

    return (
      <div className="space-y-2">
        {Object.entries(files).map(([fileType, filePath]) => {
          if (typeof filePath !== 'string') return null;
          
          const fullUrl = documentsService.getFullResultUrl(filePath as string);
          const fileName = (filePath as string).split('/').pop() || fileType;
          
          return (
            <div key={fileType} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="flex items-center space-x-2">
                <svg className="h-4 w-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-sm font-medium">{fileType.charAt(0).toUpperCase() + fileType.slice(1)}</span>
                <span className="text-xs text-gray-500">({fileName})</span>
              </div>
              <a
                href={fullUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
              >
                Download
              </a>
            </div>
          );
        })}
      </div>
    );
  };

  const renderTableData = (tables: any) => {
    if (!tables || !Array.isArray(tables)) return null;

    return (
      <div className="space-y-3">
        {tables.map((table: any, index: number) => (
          <div key={index} className="border border-gray-200 dark:border-gray-600 rounded p-3">
            <h5 className="font-medium text-sm mb-2">Table {index + 1}</h5>
            {table.markdown && (
              <div className="text-xs bg-gray-50 dark:bg-gray-800 p-2 rounded overflow-auto max-h-40">
                <pre className="whitespace-pre-wrap">{table.markdown}</pre>
              </div>
            )}
            {table.csv && (
              <div className="mt-2">
                <a
                  href={documentsService.getFullResultUrl(table.csv)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm"
                >
                  Download CSV
                </a>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center" style={{ zIndex: 9999999, backgroundColor: 'rgba(0, 0, 0, 0.5)' }}>
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg max-w-4xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-black dark:text-white">
            Parse Results: {document.title || document.filename}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-2 text-gray-600 dark:text-gray-400">Loading parse results...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-4 mb-4">
            <div className="flex">
              <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="ml-3">
                <h4 className="text-sm font-medium text-red-800 dark:text-red-200">Error Loading Results</h4>
                <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
              </div>
            </div>
          </div>
        )}

        {parseResult && (
          <div className="space-y-6">
            {/* Parse Info */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-4">
              <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-2">Parse Information</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Parser:</span>
                  <span className="ml-2 text-gray-600 dark:text-gray-400">{parseResult.parser_type}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Status:</span>
                  <span className={`ml-2 ${parseResult.status === 'completed' ? 'text-green-600' : 'text-yellow-600'}`}>
                    {parseResult.status}
                  </span>
                </div>
                {parseResult.completed_at && (
                  <div className="col-span-2">
                    <span className="font-medium text-gray-700 dark:text-gray-300">Completed:</span>
                    <span className="ml-2 text-gray-600 dark:text-gray-400">
                      {new Date(parseResult.completed_at).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Output Files */}
            {parseResult.parse_result?.files && Object.keys(parseResult.parse_result.files).length > 0 && (
              <div>
                <h4 className="font-medium text-gray-800 dark:text-gray-200 mb-3">Output Files</h4>
                {renderFileLinks(parseResult.parse_result.files)}
              </div>
            )}

            {/* Extracted Tables */}
            {parseResult.parse_result?.tables && parseResult.parse_result.tables.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-800 dark:text-gray-200 mb-3">
                  Extracted Tables ({parseResult.parse_result.tables.length})
                </h4>
                {renderTableData(parseResult.parse_result.tables)}
              </div>
            )}

            {/* Images */}
            {parseResult.parse_result?.images && parseResult.parse_result.images.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-800 dark:text-gray-200 mb-3">
                  Extracted Images ({parseResult.parse_result.images.length})
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  {parseResult.parse_result.images.map((image: any, index: number) => (
                    <div key={index} className="border border-gray-200 dark:border-gray-600 rounded p-2">
                      <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                        Image {index + 1}
                      </div>
                      {image.path && (
                        <a
                          href={documentsService.getFullResultUrl(image.path)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm"
                        >
                          View Image
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata */}
            {parseResult.parse_result?.metadata && (
              <div>
                <h4 className="font-medium text-gray-800 dark:text-gray-200 mb-3">Metadata</h4>
                <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded text-xs overflow-auto max-h-40">
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(parseResult.parse_result.metadata, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Raw Result (for debugging) */}
            <details className="border border-gray-200 dark:border-gray-600 rounded">
              <summary className="p-3 bg-gray-50 dark:bg-gray-800 cursor-pointer text-sm font-medium">
                Raw Parse Result (Debug)
              </summary>
              <div className="p-3 bg-gray-50 dark:bg-gray-800 text-xs overflow-auto max-h-60">
                <pre className="whitespace-pre-wrap">
                  {JSON.stringify(parseResult.parse_result, null, 2)}
                </pre>
              </div>
            </details>
          </div>
        )}

        <div className="flex justify-end mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}; 