#!/usr/bin/env python3
"""
Migration script to convert existing documents to the new status structure.
This moves processing_stages from metadata to the status field directly.
"""

import json
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.core.db import engine
from app.core.models.document import Document

def migrate_to_new_status_structure():
    """Migrate existing documents to use the new status structure."""
    
    with Session(engine) as session:
        # Get all documents
        documents = session.exec(select(Document)).all()
        
        print(f"Found {len(documents)} documents to migrate to new status structure")
        
        migrated_count = 0
        
        for document in documents:
            print(f"Migrating document: {document.filename} (ID: {document.id})")
            
            # Get current metadata
            metadata = document.metadata_dict or {}
            
            # Check if old processing_stages exists in metadata
            old_processing_stages = metadata.get("processing_stages", {})
            
            if old_processing_stages:
                print(f"  Converting from old metadata structure")
                
                # Convert old structure to new status structure
                current_stage = "parse"  # Default
                stage_status = "waiting"  # Default
                
                # Determine current stage and status from old structure
                for stage_name in ["upload", "parse", "chunk", "index"]:
                    stage = old_processing_stages.get(stage_name, {})
                    status = stage.get("status")
                    if status in ["waiting", "running", "failed"]:
                        current_stage = stage_name
                        stage_status = status
                        break
                
                # Create new status structure
                new_status = {
                    "current_stage": current_stage,
                    "stage_status": stage_status,
                    "stages": {}
                }
                
                # Convert each stage
                for stage_name, stage_data in old_processing_stages.items():
                    new_stage = {
                        "status": stage_data.get("status", "waiting")
                    }
                    
                    # Copy timestamps if they exist
                    if "started_at" in stage_data:
                        new_stage["started_at"] = stage_data["started_at"]
                    if "completed_at" in stage_data:
                        new_stage["completed_at"] = stage_data["completed_at"]
                    if "failed_at" in stage_data:
                        new_stage["failed_at"] = stage_data["failed_at"]
                    if "attempts" in stage_data:
                        new_stage["attempts"] = stage_data["attempts"]
                    if "error_message" in stage_data:
                        new_stage["error_message"] = stage_data["error_message"]
                    
                    # Add default config for each stage
                    if stage_name == "parse":
                        new_stage["config"] = stage_data.get("config", {
                            "do_ocr": True,
                            "do_table_structure": True,
                            "ocr_language": "en"
                        })
                    elif stage_name == "chunk":
                        new_stage["config"] = stage_data.get("config", {
                            "strategy": "recursive",
                            "chunk_size": 1000,
                            "chunk_overlap": 200
                        })
                    elif stage_name == "index":
                        new_stage["config"] = stage_data.get("config", {
                            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                            "index_type": "faiss"
                        })
                    
                    new_status["stages"][stage_name] = new_stage
                
                # Set the new status
                document.status_dict = new_status
                
                # Clean up metadata - remove processing_stages
                clean_metadata = {k: v for k, v in metadata.items() if k != "processing_stages"}
                document.metadata_dict = clean_metadata if clean_metadata else None
                
            else:
                print(f"  No old processing_stages found, initializing new structure")
                
                # Initialize with default structure
                document.status_dict = {
                    "current_stage": "parse",
                    "stage_status": "waiting", 
                    "stages": {
                        "upload": {
                            "status": "completed",
                            "started_at": document.created_at.isoformat() if document.created_at else datetime.now(timezone.utc).isoformat(),
                            "completed_at": document.created_at.isoformat() if document.created_at else datetime.now(timezone.utc).isoformat(),
                            "attempts": 1
                        },
                        "parse": {
                            "status": "waiting",
                            "config": {
                                "do_ocr": True,
                                "do_table_structure": True,
                                "ocr_language": "en"
                            }
                        },
                        "chunk": {
                            "status": "waiting",
                            "config": {
                                "strategy": "recursive",
                                "chunk_size": 1000,
                                "chunk_overlap": 200
                            }
                        },
                        "index": {
                            "status": "waiting",
                            "config": {
                                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                                "index_type": "faiss"
                            }
                        }
                    }
                }
            
            document.updated_at = datetime.now(timezone.utc)
            session.add(document)
            migrated_count += 1
        
        # Commit all changes
        session.commit()
        
        print(f"\nMigration completed!")
        print(f"- Total documents: {len(documents)}")
        print(f"- Migrated documents: {migrated_count}")

if __name__ == "__main__":
    migrate_to_new_status_structure() 