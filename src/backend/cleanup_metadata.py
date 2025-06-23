#!/usr/bin/env python3
"""
Cleanup script to migrate processing-related data from metadata to status structure
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.db import engine
from sqlmodel import Session, select
from app.core.models.document import Document
import json

def cleanup_metadata():
    """Clean up metadata by moving processing data to status structure"""
    
    print("🧹 Cleaning up document metadata...")
    print("=" * 50)
    
    with Session(engine) as session:
        documents = session.exec(select(Document)).all()
        
        print(f"📊 Processing {len(documents)} documents")
        
        updated_count = 0
        
        for doc in documents:
            metadata = doc.metadata_dict or {}
            status_dict = doc.status_dict
            
            # Keys that should NOT be in metadata (processing-related)
            processing_keys = [
                "ragparser_status", "ragparser_progress", "ragparser_state",
                "ragparser_task_id", "ragparser_error", "queue_position",
                "parsing_started_at", "parsed_at", "parsing_completed",
                "last_status_check", "result_url", "result_key", "table_keys",
                "parsed_data_processed", "parsed_content_length", "table_count",
                "result_processing_completed_at", "result_download_successful",
                "processing_error", "failed_at", "failed_stage", "pipeline_error"
            ]
            
            # Static document characteristics that SHOULD stay in metadata
            keep_keys = [
                "uploaded_by", "original_filename", 
                "docling", "structure", "binary_hash_source"
            ]
            
            # Clean metadata - keep only static document characteristics
            clean_metadata = {}
            removed_keys = []
            
            for key, value in metadata.items():
                if key in keep_keys or key.startswith("structure"):
                    clean_metadata[key] = value
                else:
                    removed_keys.append(key)
            
            # Update document if we cleaned anything
            if removed_keys:
                print(f"📄 Cleaning {doc.filename[:50]}...")
                print(f"   Removed: {', '.join(removed_keys)}")
                
                doc.metadata_dict = clean_metadata if clean_metadata else None
                session.add(doc)
                updated_count += 1
        
        # Commit all changes
        session.commit()
        
        print(f"\n✅ Cleanup completed!")
        print(f"📊 Updated {updated_count} documents")
        print("🗂️  Metadata now contains only static document characteristics")

if __name__ == "__main__":
    cleanup_metadata() 