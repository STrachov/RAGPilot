import { apiClient, fileUploadClient, API_ENDPOINTS } from '@/lib/api';
import { Document, DocumentChunk, DocumentSourceType, DocumentStagesResponse} from '@/types/ragpilot';

export interface UploadDocumentRequest {
  file: File;
  title?: string;
  source_type?: DocumentSourceType;
  source_name?: string;
  run_pipeline?: boolean;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface DocumentsListParams {
  skip?: number;
  limit?: number;
  status?: string;  // Now accepts simple status strings for filtering
  source_type?: DocumentSourceType;
}

export interface ListChunksParams {
  document_id: string;
  skip?: number;
  limit?: number;
  chunk_type?: string;
}

export const documentsService = {
  // Get list of documents
  async getDocuments(params: DocumentsListParams = {}): Promise<Document[]> {
    const { data } = await apiClient.get(API_ENDPOINTS.DOCUMENTS.LIST, {
      params,
    });
    return data;
  },

  // Get a specific document by ID
  async getDocument(id: string): Promise<Document> {
    const { data } = await apiClient.get(API_ENDPOINTS.DOCUMENTS.GET(id));
    return data;
  },

  // Upload a single document
  async uploadDocument(
    request: { file: File; source_type: DocumentSourceType; run_pipeline?: boolean },
    onProgress?: (progress: UploadProgress) => void
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('source_type', request.source_type.toString());
    
    // Add pipeline option if specified
    if (request.run_pipeline !== undefined) {
      formData.append('run_pipeline', request.run_pipeline.toString());
    }

    try {
      const response = await fileUploadClient.post<Document>(API_ENDPOINTS.DOCUMENTS.UPLOAD, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            onProgress({
              loaded: progressEvent.loaded,
              total: progressEvent.total,
              percentage: Math.round((progressEvent.loaded * 100) / progressEvent.total),
            });
          }
        },
      });

      return response.data;
    } catch (error: any) {
      console.error('Upload error details:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message,
      });

      if (error.response?.status === 422) {
        const validationErrors = error.response?.data?.detail;
        
        if (Array.isArray(validationErrors)) {
          const errorMessages = validationErrors.map((err: any) => {
            const location = err.loc ? err.loc.join('.') : 'unknown';
            const message = err.msg || err.message || 'validation error';
            return `${location}: ${message}`;
          });
          throw new Error(`Validation error: ${errorMessages.join(', ')}`);
        }
      }

      // Handle timeout specifically
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        throw new Error('Upload timeout - file may be too large or connection too slow');
      }

      throw new Error(error.response?.data?.message || error.message || 'Upload failed');
    }
  },

  // Delete a document
  async deleteDocument(id: string): Promise<{ message: string }> {
    const { data } = await apiClient.delete(API_ENDPOINTS.DOCUMENTS.DELETE(id));
    return data;
  },

  // Bulk delete documents
  async bulkDeleteDocuments(documentIds: string[]): Promise<{ deleted: string[]; failed: string[] }> {
    const deleted: string[] = [];
    const failed: string[] = [];

    // Process deletions in parallel but with some concurrency control
    const deletePromises = documentIds.map(async (id) => {
      try {
        await apiClient.delete(API_ENDPOINTS.DOCUMENTS.DELETE(id));
        deleted.push(id);
      } catch (error) {
        console.error(`Failed to delete document ${id}:`, error);
        failed.push(id);
      }
    });

    await Promise.all(deletePromises);

    return { deleted, failed };
  },

  // Get document chunks
  async getDocumentChunks(params: ListChunksParams): Promise<DocumentChunk[]> {
    const { document_id, ...queryParams } = params;
    const { data } = await apiClient.get(API_ENDPOINTS.DOCUMENTS.CHUNKS(document_id), {
      params: queryParams,
    });
    return data;
  },

  // Get download URL for a document
  async getDocumentDownloadUrl(id: string, expiration = 3600): Promise<{ download_url: string; expires_in: number }> {
    const { data } = await apiClient.get(API_ENDPOINTS.DOCUMENTS.DOWNLOAD(id), {
      params: { expiration },
    });
    return data;
  },

  // Validate file before upload
  validateFile(file: File): { isValid: boolean; error?: string } {
    // Check file size (100MB limit as per backend)
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      return {
        isValid: false,
        error: `File size must be less than ${maxSize / (1024 * 1024)}MB`,
      };
    }

    // Check file type - match backend ALLOWED_DOCUMENT_TYPES exactly
    const allowedTypes = [
      'application/pdf',
      'application/msword', // doc
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // docx
      'text/plain',
      'text/markdown', 
      'text/csv',
      'application/json',
      'application/vnd.ms-excel', // xls
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // xlsx
      'application/epub+zip', // epub
    ];

    if (!allowedTypes.includes(file.type)) {
      return {
        isValid: false,
        error: `File type ${file.type} is not supported. Supported types: PDF, Word (DOC/DOCX), Excel (XLS/XLSX), Text, Markdown, CSV, JSON, EPUB`,
      };
    }

    return { isValid: true };
  },

  // Format file size for display
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // Get file icon based on type
  getFileIcon(file: File): string {
    const type = file.type.toLowerCase();
    
    if (type.includes('pdf')) return '📄';
    if (type.includes('word') || type.includes('document')) return '📝';
    if (type.includes('excel') || type.includes('spreadsheet')) return '📊';
    if (type.includes('text') || type.includes('plain')) return '📃';
    if (type.includes('markdown')) return '📋';
    if (type.includes('csv')) return '📈';
    if (type.includes('json')) return '🔧';
    
    return '📄'; // Default file icon
  },

  // STAGE-BASED PROCESSING METHODS

  // Start or retry a specific processing stage
  async startDocumentStage(
    id: string, 
    stage: 'parse' | 'chunk-index',
    configOverrides?: Record<string, unknown>
  ): Promise<{ message: string; stages: any }> {
    const { data } = await apiClient.post(`/documents/${id}/stages/${stage}/start`, {
      config_overrides: configOverrides
    });
    return data;
  },

  // Get error details for a failed stage
  async getStageError(
    id: string, 
    stage: 'upload' | 'parse' | 'chunk' | 'index'
  ): Promise<{
    document_id: string;
    stage: string;
    error_message: string;
    failed_at: string;
    attempts: number;
    config: Record<string, unknown>;
  }> {
    const { data } = await apiClient.get(`/documents/${id}/stages/${stage}/error`);
    return data;
  },

  // Removed getStageProgress - redundant with updateDocumentStatus,

  // Reparse document with new parser configuration
  async reparseDocument(
    id: string,
    parseConfig: {
      parser_type: 'docling' | 'marker' | 'unstructured';
      do_ocr?: boolean;
      do_table_structure?: boolean;
      ocr_language?: string;
      table_extraction_method?: string;
      use_gpu?: boolean;
    }
  ): Promise<{ message: string; document_id: string; parser_type: string }> {
    const { data } = await apiClient.post(`${API_ENDPOINTS.DOCUMENTS.GET(id)}/reparse`, parseConfig);
    return data;
  },

  // Reprocess document with current global configuration
  async reprocessDocument(id: string): Promise<{ message: string; document_id: string }> {
    const { data } = await apiClient.post(`${API_ENDPOINTS.DOCUMENTS.GET(id)}/reprocess`);
    return data;
  },

  // Get document parse configuration
  async getDocumentParseConfig(id: string): Promise<{
    document_id: string;
    parse_config: any;
    available_parsers: string[];
  }> {
    const { data } = await apiClient.get(`${API_ENDPOINTS.DOCUMENTS.GET(id)}/parse-config`);
    return data;
  },

  // Get document quality metrics
  async getDocumentQualityMetrics(id: string): Promise<{
    document_id: string;
    metrics: Record<string, any>;
    overall_status: string;
  }> {
    const { data } = await apiClient.get(API_ENDPOINTS.DOCUMENTS.QUALITY_METRICS(id));
    return data;
  },

  // Get parse results with RAGParser response data
  async getParseResults(id: string): Promise<{
    document_id: string;
    parse_result: Record<string, any>;
    status: string;
    completed_at?: string;
    parser_type: string;
  }> {
    const { data } = await apiClient.get(API_ENDPOINTS.DOCUMENTS.PARSE_RESULTS(id));
    return data;
  },

  // Update document status (refresh from backend)
  async updateDocumentStatus(id: string): Promise<Document> {
    const { data } = await apiClient.post(API_ENDPOINTS.DOCUMENTS.UPDATE_STATUS(id));
    return data;
  },

  // Helper function to get full URL for RAGParser results
  getFullResultUrl(partialUrl: string): string {
    const BUCKET_URL = process.env.NEXT_PUBLIC_BUCKET_URL || 'https://pub-381250270a5e44868e19775ade02245c.r2.dev';
    // Remove leading slash if present to avoid double slashes
    const cleanPartialUrl = partialUrl.startsWith('/') ? partialUrl.slice(1) : partialUrl;
    
    // RAGParser now uses document IDs in URLs, so no special encoding handling needed
    return `${BUCKET_URL}/${cleanPartialUrl}`;
  }
};

export default documentsService; 
