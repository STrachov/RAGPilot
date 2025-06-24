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
        //console.log('Full Parse stage data:', JSON.stringify(parseStage, null, 2)); // Enhanced debug log
        
        if (parseStage.status === 'completed') {
          // Get the actual RAGParser result from the parse stage
          const ragparserResult = parseStage.result || {};
          //console.log('RAGParser result:', JSON.stringify(ragparserResult, null, 2)); // Debug log
          
          const parserUsed = parseStage.parser_used || 'unknown';
          console.log('Parser used:', parserUsed);
          
          // Always use the data from document status for completed documents
          const result: ParseResult = {
            document_id: document.id,
            status: parseStage.status,
            completed_at: parseStage.completed_at,
            parser_type: parserUsed,
            parse_result: ragparserResult
          };
          
          setParseResult(result);
          setIsLoading(false);
          //return;
        }
      }
      
      // Try API call for non-completed documents or as fallback
      try {
        const result = await documentsService.getParseResults(document.id);
        console.log('API parse result:', JSON.stringify(result, null, 2)); // Debug log
        setParseResult(result);
      } catch (apiError: any) {
        // If API fails and we have a completed parse stage, show helpful message
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

  // Helper function to render document metadata
  const renderDocumentMetadata = () => {
    if (!document.metadata) return null;

    const metadata = document.metadata;
    const structure = metadata.structure || {};
    
    return (
      <div className="space-y-4">
        <h4 className="font-medium text-gray-800 dark:text-gray-200 mb-3">Document Analysis</h4>
        
        {/* Document Structure Information */}
        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded">
          <h5 className="font-medium text-sm mb-3 text-gray-700 dark:text-gray-300">Document Structure</h5>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            {structure.page_count && (
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">Pages:</span>
                <span className="ml-2 text-gray-800 dark:text-gray-200">{structure.page_count}</span>
              </div>
            )}
            {structure.table_count !== undefined && (
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">Tables:</span>
                <span className="ml-2 text-gray-800 dark:text-gray-200">{structure.table_count}</span>
              </div>
            )}
            {structure.image_count !== undefined && (
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">Images:</span>
                <span className="ml-2 text-gray-800 dark:text-gray-200">{structure.image_count}</span>
              </div>
            )}
            {structure.word_count && (
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">Words:</span>
                <span className="ml-2 text-gray-800 dark:text-gray-200">{structure.word_count.toLocaleString()}</span>
              </div>
            )}
            {structure.text_length && (
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">Characters:</span>
                <span className="ml-2 text-gray-800 dark:text-gray-200">{structure.text_length.toLocaleString()}</span>
              </div>
            )}
            {structure.language && (
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">Language:</span>
                <span className="ml-2 text-gray-800 dark:text-gray-200">{structure.language}</span>
              </div>
            )}
            {structure.is_scanned !== undefined && (
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">Scanned:</span>
                <span className={`ml-2 ${structure.is_scanned ? 'text-orange-600' : 'text-green-600'}`}>
                  {structure.is_scanned ? 'Yes' : 'No'}
                </span>
              </div>
            )}
            {structure.mime_type && (
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">MIME Type:</span>
                <span className="ml-2 text-gray-800 dark:text-gray-200 font-mono text-xs">{structure.mime_type}</span>
              </div>
            )}
          </div>
          
          {structure.rotated_pages && structure.rotated_pages.length > 0 && (
            <div className="mt-3">
              <span className="font-medium text-gray-600 dark:text-gray-400">Rotated Pages:</span>
              <span className="ml-2 text-gray-800 dark:text-gray-200">{structure.rotated_pages.join(', ')}</span>
            </div>
          )}
          
          {structure.analysis_source && (
            <div className="mt-3">
              <span className="font-medium text-gray-600 dark:text-gray-400">Analysis Source:</span>
              <span className={`ml-2 px-2 py-1 rounded text-xs ${
                structure.analysis_source === 'ragparser' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                structure.analysis_source === 'fallback' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
              }`}>
                {structure.analysis_source}
              </span>
            </div>
          )}
          
          {structure.analysis_limitations && (
            <div className="mt-3">
              <span className="font-medium text-gray-600 dark:text-gray-400">Limitations:</span>
              <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                {Object.entries(structure.analysis_limitations).map(([key, value]) => (
                  <div key={key} className="ml-2">• {key}: {value}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Helper function to render file links from RAGParser results
  const renderResultFiles = (result: any) => {
    if (!result) return null;

    const files = [];
    
    // Main result file (JSON)
    if (result.result_key) {
      files.push({
        type: 'Main Result (JSON)',
        key: result.result_key,
        filename: result.result_key.split('/').pop() || 'result.json',
        format: 'JSON'
      });
    }
    
    // Table files
    if (result.table_keys && Array.isArray(result.table_keys)) {
      result.table_keys.forEach((tableKey: string, index: number) => {
        files.push({
          type: `Table ${index + 1}`,
          key: tableKey,
          filename: tableKey.split('/').pop() || `table_${index}.csv`,
          format: tableKey.endsWith('.json') ? 'JSON' : 'CSV'
        });
      });
    }

    if (files.length === 0) return null;

    return (
      <div className="space-y-3">
        <h4 className="font-medium text-gray-800 dark:text-gray-200">Parse Result Files</h4>
        {files.map((file, index) => {
          const fullUrl = documentsService.getFullResultUrl(file.key);
          
          return (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  {file.format === 'JSON' ? (
                    <svg className="h-5 w-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2h2a2 2 0 002-2z" />
                    </svg>
                  )}
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{file.type}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {file.filename} • {file.format}
                  </div>
                </div>
              </div>
              <a
                href={fullUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200 dark:hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <svg className="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download
              </a>
            </div>
          );
        })}
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center" style={{ zIndex: 9999999, backgroundColor: 'rgba(0, 0, 0, 0.5)' }}>
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-semibold text-black dark:text-white">
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
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-4 mb-6">
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

        {!isLoading && !error && (
          <div className="space-y-8">
            {/* Document Information Summary */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-4">
              <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-3">Document Information</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Filename:</span>
                  <div className="text-gray-600 dark:text-gray-400 break-all">{document.filename}</div>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Size:</span>
                  <div className="text-gray-600 dark:text-gray-400">{documentsService.formatFileSize(document.file_size)}</div>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Content Type:</span>
                  <div className="text-gray-600 dark:text-gray-400 font-mono text-xs">{document.content_type}</div>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">Uploaded:</span>
                  <div className="text-gray-600 dark:text-gray-400">{new Date(document.created_at).toLocaleString()}</div>
                </div>
                {parseResult && (
                  <>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Parser:</span>
                      <div className={`${parseResult.parser_type === 'unknown' ? 'text-orange-600 dark:text-orange-400' : 'text-gray-600 dark:text-gray-400'}`}>
                        {parseResult.parser_type}
                        {parseResult.parser_type === 'unknown' && (
                          <span className="text-xs ml-1">(detection failed)</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-300">Parse Status:</span>
                      <span className={`ml-2 px-2 py-1 rounded text-xs ${
                        parseResult.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                        parseResult.status === 'running' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                        parseResult.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                        'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                      }`}>
                        {parseResult.status}
                      </span>
                    </div>
                    {parseResult.completed_at && (
                      <div>
                        <span className="font-medium text-gray-700 dark:text-gray-300">Completed:</span>
                        <div className="text-gray-600 dark:text-gray-400 text-xs">
                          {new Date(parseResult.completed_at).toLocaleString()}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* Render Document Metadata */}
            {renderDocumentMetadata()}

            {/* Render Parse Result Files */}
            {parseResult?.parse_result && renderResultFiles(parseResult.parse_result)}
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