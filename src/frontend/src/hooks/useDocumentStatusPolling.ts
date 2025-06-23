import { useQuery } from "@tanstack/react-query";
import { documentsService } from "@/services/documents";
import { Document, DocumentStatusStructure } from "@/types/ragpilot";

interface UseDocumentStatusPollingOptions {
  enabled?: boolean;
}

/**
 * Hook for polling document status updates
 * Only polls when documents have parsing status = "running"
 * Returns updated documents - components handle their own cache updates
 */
export const useDocumentStatusPolling = (
  documentIds: string[], 
  options: UseDocumentStatusPollingOptions = {}
) => {
  const { enabled = true } = options;

  return useQuery({
    queryKey: ['documents-status-polling', ...documentIds.sort()], // Sort IDs for stable key
    queryFn: async () => {
      if (documentIds.length === 0) return [];
      
      // Fetch updated status for all documents
      const promises = documentIds.map(id => 
        documentsService.updateDocumentStatus(id).catch(error => {
          console.warn(`Failed to update status for document ${id}:`, error);
          return null; // Return null for failed requests
        })
      );
      
      const results = await Promise.all(promises);
      const validDocuments = results.filter((doc): doc is Document => doc !== null);
      
      return validDocuments;
    },
    refetchInterval: (query) => {
      const data = query.state.data;
      
      if (!enabled || !data || data.length === 0) {
        return false; // Stop polling
      }
      
      // Check if any document has any running stage
      const hasRunningStage = data.some((doc: Document) => {
        if (typeof doc.status === 'string') {
          return doc.status === 'processing'; // Backward compatibility
        }
        
        const status = doc.status as DocumentStatusStructure;
        if (!status?.stages) return false;
        
        // Check if any stage is running
        return Object.values(status.stages).some(stage => 
          stage && stage.status === 'running'
        );
      });
      
      // Only poll if there are documents with running parse stages
      return hasRunningStage ? 15000 : false; // 15 seconds
    },
    refetchIntervalInBackground: false, // Stop polling when tab not active
    enabled: enabled && documentIds.length > 0,
    // Don't show stale data warning since we expect data to change
    staleTime: 0,
  });
}; 