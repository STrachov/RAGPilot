#!/usr/bin/env python3
"""
Script to check document status structures after migration.
"""

import json
from sqlmodel import Session, select
from app.core.db import engine
from app.core.models.document import Document

def check_document_statuses():
    """Check the status structure of all documents."""
    
    with Session(engine) as session:
        # Get all documents
        documents = session.exec(select(Document)).all()
        
        print(f"Checking {len(documents)} documents...\n")
        
        for i, document in enumerate(documents, 1):
            print(f"Document {i}: {document.filename}")
            print(f"  ID: {document.id}")
            print(f"  Status: {document.status}")
            print(f"  Current Stage: {document.current_stage}")
            print(f"  Overall Status: {document.overall_status}")
            
            # Show processing stages
            stages = document.processing_stages
            print(f"  Processing Stages:")
            for stage_name, stage_info in stages.items():
                status = stage_info.get('status', 'unknown')
                print(f"    {stage_name}: {status}")
                
                # Show config if exists
                if 'config' in stage_info:
                    print(f"      config: {json.dumps(stage_info['config'], indent=8)}")
            
            print(f"  Metadata JSON length: {len(document.metadata_json or '')} chars")
            print("-" * 80)

if __name__ == "__main__":
    check_document_statuses() 