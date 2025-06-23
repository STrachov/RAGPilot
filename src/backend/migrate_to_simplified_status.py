#!/usr/bin/env python3
"""
Migration script to convert documents to the new simplified status structure.
This removes redundant current_stage and stage_status fields and combines chunk/index stages.
"""

import json
from datetime import datetime, timezone
from sqlmodel import Session, select

def migrate_to_simplified_status():
    """Migrate existing documents to use the simplified status structure."""
    from app.core.db import engine
    from app.core.models.document import Document
    
    with Session(engine) as session:
        # Get all documents
        documents = session.exec(select(Document)).all()
        
        print(f"Found {len(documents)} documents to migrate to simplified status structure")
        
        migrated_count = 0
        
        for document in documents:
            print(f"Migrating document: {document.filename} (ID: {document.id})")
            
            try:
                # Get current status
                current_status = document.status_dict
                
                if "stages" not in current_status:
                    print(f"  No stages found, skipping")
                    continue
                
                old_stages = current_status.get("stages", {})
                
                # Create new simplified structure
                new_status = {
                    "stages": {}
                }
                
                # Migrate upload stage (unchanged)
                if "upload" in old_stages:
                    new_status["stages"]["upload"] = old_stages["upload"]
                else:
                    new_status["stages"]["upload"] = {
                        "status": "completed",
                        "started_at": document.created_at.isoformat() if document.created_at else datetime.now(timezone.utc).isoformat(),
                        "completed_at": document.created_at.isoformat() if document.created_at else datetime.now(timezone.utc).isoformat(),
                        "attempts": 1
                    }
                
                # Migrate parse stage (unchanged)
                if "parse" in old_stages:
                    new_status["stages"]["parse"] = old_stages["parse"]
                else:
                    new_status["stages"]["parse"] = {
                        "status": "waiting",
                        "config": {
                            "do_ocr": True,
                            "extract_tables": True,
                            "extract_images": False,
                            "ocr_language": "en"
                        }
                    }
                
                # Combine chunk and index stages into chunk-index
                chunk_stage = old_stages.get("chunk", {})
                index_stage = old_stages.get("index", {})
                
                # Determine combined status
                chunk_status = chunk_stage.get("status", "waiting")
                index_status = index_stage.get("status", "waiting")
                
                if chunk_status == "failed" or index_status == "failed":
                    combined_status = "failed"
                    combined_error = chunk_stage.get("error_message") or index_stage.get("error_message")
                    combined_failed_at = chunk_stage.get("failed_at") or index_stage.get("failed_at")
                elif chunk_status == "running" or index_status == "running":
                    combined_status = "running"
                elif chunk_status == "completed" and index_status == "completed":
                    combined_status = "completed"
                elif chunk_status == "completed":
                    combined_status = "waiting"  # Chunk done, index waiting
                else:
                    combined_status = "waiting"
                
                # Create combined chunk-index stage
                new_chunk_index = {
                    "status": combined_status,
                    "config": {
                        # Chunking configuration
                        "chunk_strategy": chunk_stage.get("config", {}).get("strategy", "paragraph"),
                        "chunk_size": chunk_stage.get("config", {}).get("chunk_size", 1000),
                        "chunk_overlap": chunk_stage.get("config", {}).get("chunk_overlap", 200),
                        # Indexing configuration
                        "model_name": index_stage.get("config", {}).get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
                        "model_type": index_stage.get("config", {}).get("model_type", "sentence-transformers"),
                        "dimensions": index_stage.get("config", {}).get("dimensions", 384),
                        "index_type": index_stage.get("config", {}).get("index_type", "faiss"),
                        "similarity_metric": index_stage.get("config", {}).get("similarity_metric", "cosine")
                    }
                }
                
                # Add timing information
                if chunk_stage.get("started_at"):
                    new_chunk_index["started_at"] = chunk_stage["started_at"]
                if combined_status == "completed" and index_stage.get("completed_at"):
                    new_chunk_index["completed_at"] = index_stage["completed_at"]
                elif combined_status == "completed" and chunk_stage.get("completed_at"):
                    new_chunk_index["completed_at"] = chunk_stage["completed_at"]
                if combined_status == "failed":
                    if combined_failed_at:
                        new_chunk_index["failed_at"] = combined_failed_at
                    if combined_error:
                        new_chunk_index["error_message"] = combined_error
                
                # Add attempts
                chunk_attempts = chunk_stage.get("attempts", 0)
                index_attempts = index_stage.get("attempts", 0)
                if chunk_attempts > 0 or index_attempts > 0:
                    new_chunk_index["attempts"] = max(chunk_attempts, index_attempts)
                
                # Add chunks_created if available
                if chunk_stage.get("chunks_created"):
                    new_chunk_index["chunks_created"] = chunk_stage["chunks_created"]
                
                new_status["stages"]["chunk-index"] = new_chunk_index
                
                # Set the new status
                document.status_dict = new_status
                document.updated_at = datetime.now(timezone.utc)
                session.add(document)
                
                migrated_count += 1
                print(f"  ✓ Migrated to simplified structure")
                
            except Exception as e:
                print(f"  ✗ Error migrating document {document.id}: {e}")
                continue
        
        # Commit all changes
        session.commit()
        print(f"\nMigration completed: {migrated_count} documents migrated to simplified status structure")

if __name__ == "__main__":
    migrate_to_simplified_status() 