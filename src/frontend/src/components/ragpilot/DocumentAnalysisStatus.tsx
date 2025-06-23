"use client";

import React from 'react';
import { Document, DocumentMetadata } from '@/types/ragpilot';

interface DocumentAnalysisStatusProps {
  document: Document;
  className?: string;
}

export const DocumentAnalysisStatus: React.FC<DocumentAnalysisStatusProps> = ({ 
  document, 
  className = "" 
}) => {
  const structure = document.metadata?.structure;
  
  if (!structure) {
    return (
      <div className={`text-sm text-gray-500 dark:text-gray-400 ${className}`}>
        Analysis pending...
      </div>
    );
  }

  // Check if parsing failed or is incomplete
  if (structure.parsing_failed) {
    return (
      <div className={`${className}`}>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-red-500 rounded-full"></div>
          <span className="text-sm text-red-600 dark:text-red-400">
            Analysis failed
          </span>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Document parsing encountered errors
        </div>
      </div>
    );
  }

  if (structure.parsing_incomplete) {
    return (
      <div className={`${className}`}>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
          <span className="text-sm text-yellow-600 dark:text-yellow-400">
            Analysis incomplete
          </span>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Limited document information available
        </div>
        {structure.table_count !== undefined && (
          <div className="text-xs text-gray-600 dark:text-gray-300 mt-1">
            Tables found: {structure.table_count}
          </div>
        )}
      </div>
    );
  }

  // Show complete analysis data
  return (
    <div className={`${className}`}>
      <div className="flex items-center space-x-2 mb-2">
        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
        <span className="text-sm text-green-600 dark:text-green-400">
          Analysis complete
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-300">
        {structure.page_count !== undefined && (
          <div>Pages: {structure.page_count}</div>
        )}
        {structure.word_count !== undefined && (
          <div>Words: {structure.word_count.toLocaleString()}</div>
        )}
        {structure.table_count !== undefined && (
          <div>Tables: {structure.table_count}</div>
        )}
        {structure.image_count !== undefined && (
          <div>Images: {structure.image_count}</div>
        )}
        {structure.language && (
          <div>Language: {structure.language.toUpperCase()}</div>
        )}
        {structure.is_scanned !== undefined && (
          <div>Scanned: {structure.is_scanned ? 'Yes' : 'No'}</div>
        )}
      </div>
      
      {structure.text_length !== undefined && (
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          {(structure.text_length / 1000).toFixed(1)}k characters
        </div>
      )}
    </div>
  );
};

export default DocumentAnalysisStatus; 