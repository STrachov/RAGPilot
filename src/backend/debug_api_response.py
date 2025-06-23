#!/usr/bin/env python3
"""
Debug script to see what the documents API is returning.
"""

import json
from sqlmodel import Session, select
from app.core.db import engine
from app.core.models.document import Document

def debug_api_response():
    """Check what the API would return for documents."""
    
    with Session(engine) as session:
        # Get all documents like the API would
        documents = session.exec(select(Document)).all()
        
        print("=== API RESPONSE DEBUG ===")
        print(f"Found {len(documents)} documents\n")
        
        for i, document in enumerate(documents[:3], 1):  # Show first 3
            print(f"Document {i}: {document.filename}")
            print(f"  ID: {document.id}")
            
            # This is what the API serializes
            doc_dict = {
                "id": document.id,
                "filename": document.filename,
                "title": document.title,
                "source_type": document.source_type,
                "source_name": document.source_name,
                "file_path": document.file_path,
                "content_type": document.content_type,
                "file_size": document.file_size,
                "status": document.status,  # This is the key field
                "metadata": document.metadata_dict,
                "created_at": document.created_at.isoformat() if document.created_at else None,
                "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            }
            
            print(f"  Status type: {type(document.status)}")
            print(f"  Status value: {document.status}")
            print(f"  Status (raw from DB): {getattr(document, '_sa_instance_state', {}).get('attrs', {}).get('status', 'N/A')}")
            
            # Show what status_dict property returns
            try:
                status_dict = document.status_dict
                print(f"  Status dict: {json.dumps(status_dict, indent=2)}")
            except Exception as e:
                print(f"  Status dict error: {e}")
            
            print("-" * 50)

if __name__ == "__main__":
    debug_api_response() 