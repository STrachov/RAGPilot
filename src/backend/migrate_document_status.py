#!/usr/bin/env python3
"""
Migration script to update existing documents with proper processing stages structure.
Run this script to migrate documents that were created before the complex status system.
"""

import json
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.core.db import engine
from app.core.models.document import Document
from app.core.config.constants import StageStatus

def migrate_document_statuses():
    """Migrate existing documents to use the complex processing stages structure."""
    
    with Session(engine) as session:
        # Get all documents
        documents = session.exec(select(Document)).all()
        
        print(f"Found {len(documents)} documents to migrate")
        
        migrated_count = 0
        
        for document in documents:
            # Check if document already has processing_stages
            metadata = document.metadata_dict or {}
            
            if "processing_stages" not in metadata:
                print(f"Migrating document: {document.filename} (ID: {document.id})")
                
                # Initialize processing stages structure
                metadata["processing_stages"] = {
                    "upload": {
                        "status": StageStatus.COMPLETED.value,
                        "started_at": document.created_at.isoformat() if document.created_at else datetime.now(timezone.utc).isoformat(),
                        "completed_at": document.created_at.isoformat() if document.created_at else datetime.now(timezone.utc).isoformat(),
                        "attempts": 1
                    },
                    "parse": {
                        "status": StageStatus.WAITING.value if document.status == "pending" else StageStatus.FAILED.value if document.status == "failed" else StageStatus.COMPLETED.value,
                        "config": {
                            "do_ocr": True,
                            "extract_tables": True,
                            "extract_images": False,
                            "ocr_language": "en"
                        }
                    },
                    "chunk": {
                        "status": StageStatus.WAITING.value,
                        "config": {
                            "strategy": "paragraph",
                            "chunk_size": 1000,
                            "chunk_overlap": 200
                        }
                    },
                    "index": {
                        "status": StageStatus.WAITING.value,
                        "config": {
                            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                            "model_type": "sentence-transformers", 
                            "dimensions": 384,
                            "index_type": "faiss",
                            "similarity_metric": "cosine"
                        }
                    }
                }
                
                # Update the document metadata
                document.metadata_dict = metadata
                document.updated_at = datetime.now(timezone.utc)
                
                session.add(document)
                migrated_count += 1
            else:
                print(f"Skipping document {document.filename} - already has processing_stages")
        
        # Commit all changes
        session.commit()
        
        print(f"\nMigration completed!")
        print(f"- Total documents: {len(documents)}")
        print(f"- Migrated documents: {migrated_count}")
        print(f"- Already migrated: {len(documents) - migrated_count}")

if __name__ == "__main__":
    migrate_document_statuses() 