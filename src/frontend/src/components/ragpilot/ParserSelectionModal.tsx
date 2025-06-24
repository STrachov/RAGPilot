"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { Document } from "@/types/ragpilot";

interface ParseConfig {
  parser_type: "docling" | "marker" | "unstructured";
  do_ocr: boolean;
  extract_tables: boolean;
  extract_images: boolean;
  ocr_language: string;
  preserve_formatting: boolean;
  handle_multi_column: boolean;
}

interface ParserSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: Document;
}

const PARSER_OPTIONS = [
  {
    value: "docling" as const,
    label: "Docling",
    description: "IBM's advanced PDF parser with excellent table and structure preservation",
    recommended: true
  },
  {
    value: "marker" as const,
    label: "Marker", 
    description: "Fast PDF to markdown converter with good formatting preservation",
    recommended: false
  },
  {
    value: "unstructured" as const,
    label: "Unstructured",
    description: "General-purpose document parser supporting multiple formats",
    recommended: false
  }
];

const OCR_LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ua", label: "Ukrainian" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "it", label: "Italian" },
  { value: "pt", label: "Portuguese" },
  { value: "ru", label: "Russian" },
  { value: "zh", label: "Chinese" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" }
];



export const ParserSelectionModal: React.FC<ParserSelectionModalProps> = ({
  isOpen,
  onClose,
  document
}) => {
  const queryClient = useQueryClient();
  
  const [config, setConfig] = useState<ParseConfig>({
    parser_type: "docling", // Default to docling as recommended
    do_ocr: true,
    extract_tables: true,
    extract_images: false,
    ocr_language: "en",
    preserve_formatting: true,
    handle_multi_column: true
  });

  const [isLoadingConfig, setIsLoadingConfig] = useState(false);

  // Load existing parse config when modal opens
  useEffect(() => {
    if (isOpen && document?.id) {
      setIsLoadingConfig(true);
      documentsService.getDocumentParseConfig(document.id)
        .then((response) => {
          if (response.parse_config) {
            // Map the backend config to frontend config
            setConfig({
              parser_type: response.parse_config.parser_type || "docling",
              do_ocr: response.parse_config.do_ocr ?? true,
              extract_tables: response.parse_config.extract_tables ?? true,
              extract_images: response.parse_config.extract_images ?? false,
              ocr_language: response.parse_config.ocr_language || "en",
              preserve_formatting: response.parse_config.preserve_formatting ?? true,
              handle_multi_column: response.parse_config.handle_multi_column ?? true
            });
          }
        })
        .catch((error) => {
          console.warn('Failed to load existing parse config, using defaults:', error);
          // Keep defaults if loading fails
        })
        .finally(() => {
          setIsLoadingConfig(false);
        });
    }
  }, [isOpen, document?.id]);

  const reparseDocument = useMutation({
    mutationFn: async (parseConfig: ParseConfig) => {
      return documentsService.reparseDocument(document.id, parseConfig);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document', document.id] });
      alert(data.message);
      onClose();
    },
    onError: (error: any) => {
      console.error('Failed to reparse document:', error);
      alert(`Failed to reparse document: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (confirm(`Are you sure you want to reparse "${document.title || document.filename}" with ${config.parser_type} parser? This will restart the document processing from the beginning.`)) {
      reparseDocument.mutate(config);
    }
  };

  if (!isOpen) return null;

  const modalContent = (
    <div className="fixed inset-0 flex items-center justify-center" style={{ zIndex: 9999999, backgroundColor: 'rgba(0, 0, 0, 0.5)' }}>
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-2xl border border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
            Configure and Parse Document
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

        <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-start space-x-3">
            <svg className="h-5 w-5 text-blue-500 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Document: {document.title || document.filename}
              </h4>
              <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                This will parse the document with a new parser configuration and restart all processing stages.
                {isLoadingConfig && (
                  <span className="block mt-1 text-xs italic">Loading current configuration...</span>
                )}
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Parser Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Parser Type
            </label>
            <div className="space-y-3">
              {PARSER_OPTIONS.map((parser) => (
                <div
                  key={parser.value}
                  className={`relative border rounded-lg p-4 cursor-pointer transition-colors ${
                    config.parser_type === parser.value
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                  onClick={() => setConfig({ ...config, parser_type: parser.value })}
                >
                  <div className="flex items-start space-x-3">
                    <input
                      disabled={parser.value !== "docling"}
                      type="radio"
                      name="parser_type"
                      value={parser.value}
                      checked={config.parser_type === parser.value}
                      onChange={() => setConfig({ ...config, parser_type: parser.value })}
                      className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                    />
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {parser.label}
                        </span>
                        {parser.recommended && (
                          <span className="px-2 py-1 text-xs bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 rounded">
                            Recommended
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {parser.description}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Configuration Options */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-white">Processing Options</h4>
              
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={config.do_ocr}
                  onChange={(e) => setConfig({ ...config, do_ocr: e.target.checked })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Enable OCR</span>
              </label>

              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={config.extract_tables}
                  onChange={(e) => setConfig({ ...config, extract_tables: e.target.checked })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Extract Tables</span>
              </label>

              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={config.extract_images}
                  onChange={(e) => setConfig({ ...config, extract_images: e.target.checked })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Extract Images</span>
              </label>

              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={config.preserve_formatting}
                  onChange={(e) => setConfig({ ...config, preserve_formatting: e.target.checked })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Preserve Formatting</span>
              </label>

              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={config.handle_multi_column}
                  onChange={(e) => setConfig({ ...config, handle_multi_column: e.target.checked })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Handle Multi-Column Layout</span>
              </label>
            </div>

            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-white">Advanced Settings</h4>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  OCR Language
                </label>
                <select
                  value={config.ocr_language}
                  onChange={(e) => setConfig({ ...config, ocr_language: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  {OCR_LANGUAGES.map((lang) => (
                    <option key={lang.value} value={lang.value}>
                      {lang.label}
                    </option>
                  ))}
                </select>
              </div>


            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={reparseDocument.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {reparseDocument.isPending ? 'Starting Reparse...' : 'Reparse Document'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return typeof window !== 'undefined' ? createPortal(modalContent, window.document.body) : null;
}; 