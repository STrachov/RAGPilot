#!/usr/bin/env python3
"""
Debug script to check actual database content and see what's really stored.
"""

import json
from sqlmodel import Session, select, text
from app.core.db import engine
from app.core.models.document import Document

def debug_database_content():
    """Check what's actually in the database."""
    
    with Session(engine) as session:
        print("=== RAW DATABASE QUERY ===")
        # Raw SQL query to see exactly what's in the database
        result = session.exec(text("""
            SELECT id, filename, status, metadata, created_at, updated_at 
            FROM documents 
            ORDER BY created_at DESC 
            LIMIT 3
        """))
        
        for row in result:
            print(f"ID: {row[0]}")
            print(f"Filename: {row[1]}")
            print(f"Status: {row[2]}")
            print(f"Metadata: {row[3]}")
            print(f"Created: {row[4]}")
            print(f"Updated: {row[5]}")
            print("-" * 80)
        
        print("\n=== SQLMODEL QUERY ===")
        # SQLModel query to see what the model returns
        documents = session.exec(select(Document).order_by(Document.created_at.desc()).limit(3)).all()
        
        for doc in documents:
            print(f"Document: {doc.filename}")
            print(f"  Simple status: {doc.status}")
            print(f"  Metadata dict: {doc.metadata_dict}")
            print(f"  Processing stages: {doc.processing_stages}")
            print(f"  Current stage: {doc.current_stage}")
            print(f"  Overall status: {doc.overall_status}")
            print("-" * 80)

if __name__ == "__main__":
    debug_database_content() 