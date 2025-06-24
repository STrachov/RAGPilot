// User types
export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  role: string;
  permissions: string[];
  last_login?: string;
  created_at: string;
  updated_at: string;
  preferences?: Record<string, unknown>;
}

// Document status structure - your new design
export interface DocumentStageInfo {
  status: "waiting" | "running" | "completed" | "failed";
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error_message?: string;
  attempts?: number;
  config?: Record<string, unknown>;
  // Additional fields for parse stage
  result_key?: string;
  table_keys?: string[];
  progress?: number;
  ragparser_task_id?: string;
  queue_position?: number;
  last_check?: string;
  result?: Record<string, unknown>;
  parser_used?: string;
  file_size?: number;
  pages_processed?: number;
  // Allow any additional fields that might be present in database
  [key: string]: any;
}

export interface DocumentStatusStructure {
  stages: {
    upload: DocumentStageInfo;
    parse: DocumentStageInfo;
    "chunk-index": DocumentStageInfo;
  };
}

export enum DocumentSourceType {
  PDF = "pdf",
  EMAIL = "email",
  REPORT = "report",
  SHAREPOINT = "sharepoint",
  OTHER = "other"
}

export interface Document {
  id: string;
  filename: string;
  title: string;
  source_type: DocumentSourceType;
  source_name?: string;
  file_path: string;
  content_type: string;
  file_size: number;
  status: DocumentStatusStructure | string; // Can be complex JSON structure or simple string for backward compatibility
  metadata?: DocumentMetadata;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// Helper functions for working with the new status structure
export const getOverallStatus = (status: DocumentStatusStructure | string): string => {
  // Handle old simple string status
  if (typeof status === 'string') {
    return status;
  }
  
  // Handle new complex status structure
  if (!status || !status.stages) {
    return 'unknown';
  }
  
  const stages = status.stages;
  
  // Check if any stage failed
  for (const stage of Object.values(stages)) {
    if (stage && stage.status === "failed") return "failed";
  }
  
  // Check if any stage is running
  for (const stage of Object.values(stages)) {
    if (stage && stage.status === "running") return "processing";
  }
  
  // Check if all stages are completed
  const allCompleted = Object.values(stages).every(stage => stage && stage.status === "completed");
  if (allCompleted) return "completed";
  
  return "pending";
};

export const getCurrentStageProgress = (status: DocumentStatusStructure | string): number => {
  // Handle old simple string status
  if (typeof status === 'string') {
    switch (status) {
      case 'completed': return 100;
      case 'failed': return 0;
      default: return 50; // Assume halfway for unknown statuses
    }
  }
  
  // Handle new complex status structure
  if (!status || !status.stages) {
    return 0;
  }
  
  const stageOrder = ["upload", "parse", "chunk-index"];
  const completedCount = Object.entries(status.stages).filter(([_, stage]) => stage && stage.status === "completed").length;
  
  return Math.round((completedCount / stageOrder.length) * 100);
};

export const getStageDisplayName = (stage: string): string => {
  const names: Record<string, string> = {
    upload: "Upload",
    parse: "Parse",
    "chunk-index": "Chunk",
  };
  return names[stage] || stage;
};

export const getCurrentStageName = (status: DocumentStatusStructure | string): string => {
  // Handle old simple string status
  if (typeof status === 'string') {
    return status;
  }
  
  // Handle new complex status structure
  if (!status || !status.stages) {
    return 'unknown';
  }
  
  const stageOrder = ["upload", "parse", "chunk-index"];
  
  // Find the first non-completed stage
  for (const stageName of stageOrder) {
    const stage = status.stages[stageName as keyof typeof status.stages];
    if (stage && stage.status !== "completed") {
      return stageName;
    }
  }
  
  // If all stages are completed, return the last stage
  return stageOrder[stageOrder.length - 1];
};

export const getCurrentStageStatus = (status: DocumentStatusStructure | string): string => {
  // Handle old simple string status
  if (typeof status === 'string') {
    return status;
  }
  
  // Handle new complex status structure
  if (!status || !status.stages) {
    return 'unknown';
  }
  
  const currentStageName = getCurrentStageName(status);
  const currentStage = status.stages[currentStageName as keyof typeof status.stages];
  return currentStage ? currentStage.status : 'unknown';
};

// Backward compatibility types
export enum ProcessingStage {
  UPLOAD = "upload",
  PARSE = "parse",
  CHUNK = "chunk", 
  INDEX = "index"
}

export enum StageStatus {
  WAITING = "waiting",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed"
}

export interface ProcessingStageInfo {
  status: StageStatus;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error_message?: string;
  attempts?: number;
  config_overrides?: Record<string, unknown>;
  chunks_created?: number;
}

export interface DocumentProcessingStages {
  upload: ProcessingStageInfo;
  parse: ProcessingStageInfo;
  chunk: ProcessingStageInfo;
  index: ProcessingStageInfo;
}

export interface DocumentStagesResponse {
  document_id: string;
  current_stage: string;
  overall_status: string;
  stages: DocumentProcessingStages;
}

// Admin configuration types
export enum ChunkingStrategy {
  RECURSIVE = "recursive",
  SEMANTIC = "semantic",
  TOKEN = "token"
}

export enum EmbeddingModel {
  OPENAI = "openai",
  COHERE = "cohere",
  LOCAL = "local"
}

export enum IndexType {
  PINECONE = "pinecone",
  WEAVIATE = "weaviate",
  CHROMA = "chroma"
}

export enum RetrievalMethod {
  SEMANTIC = "semantic",
  KEYWORD = "keyword", 
  HYBRID = "hybrid"
}

export enum LLMProvider {
  OPENAI = "openai",
  ANTHROPIC = "anthropic",
  LOCAL = "local"
}

export interface SystemStats {
  total_documents: number;
  total_chunks: number;
  total_queries: number;
  active_users: number;
  storage_used_mb: number;
}

export interface ChunkingConfig {
  strategy: ChunkingStrategy;
  chunk_size: number;
  chunk_overlap: number;
  separators?: string[];
}

export interface EmbeddingConfig {
  model_name: string;
  model_type: EmbeddingModel;
  dimensions: number;
  api_key?: string;
}

export interface IndexConfig {
  name: string;
  index_type: IndexType;
  dimensions: number;
  similarity_metric: string;
  connection_params?: Record<string, unknown>;
}

export interface RetrievalStrategy {
  method: RetrievalMethod;
  top_k: number;
  score_threshold?: number;
  semantic_weight?: number;
  keyword_weight?: number;
}

export interface LLMConfig {
  name: string;
  provider: LLMProvider;
  model_name: string;
  max_tokens: number;
  temperature: number;
  api_key?: string;
}

export interface PromptTemplates {
  qa: string;
  summarize: string;
}

// API Response types
export interface APIResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  count: number;
  skip: number;
  limit: number;
}

// Document metadata structure
export interface DocumentMetadata {
  structure?: {
    // Real analysis data (only when RAGParser succeeds)
    page_count?: number;
    table_count?: number;
    image_count?: number;
    text_length?: number;
    word_count?: number;
    is_scanned?: boolean;
    language?: string;
    rotated_pages?: number[];
    mime_type?: string;
    
    // Analysis status indicators
    parsing_incomplete?: boolean;
    parsing_failed?: boolean;
    analysis_source?: 'ragparser' | 'fallback' | 'error';
    
    // Limitations when parsing fails
    analysis_limitations?: {
      page_count?: string;
      text_analysis?: string;
      image_analysis?: string;
      language_detection?: string;
    };
    
    // Legacy fields for backward compatibility
    has_tables?: boolean;
  };
  [key: string]: any;
} 