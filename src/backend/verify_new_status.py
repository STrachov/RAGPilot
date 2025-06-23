#!/usr/bin/env python3
"""
Verification script to check the new status structure.
"""

import json
from sqlmodel import Session, select, text
from app.core.db import engine
from app.core.models.document import Document

def verify_new_status_structure():
    """Verify the new status structure is working correctly."""
    
    with Session(engine) as session:
        print("=== CHECKING NEW STATUS STRUCTURE ===\n")
        
        # Raw database query to see what's actually stored
        print("1. RAW DATABASE STATUS CONTENT:")
        result = session.exec(text("""
            SELECT id, filename, status
            FROM documents 
            ORDER BY created_at DESC 
            LIMIT 2
        """))
        
        for row in result:
            print(f"Document: {row[1]}")
            print(f"Status (raw): {row[2][:200]}...")  # First 200 chars
            try:
                status_json = json.loads(row[2])
                print(f"Status parsed: {json.dumps(status_json, indent=2)}")
            except Exception as e:
                print(f"Status parse error: {e}")
            print("-" * 60)
        
        print("\n2. SQLMODEL PROPERTIES:")
        # SQLModel query to test properties
        documents = session.exec(select(Document).order_by(Document.created_at.desc()).limit(2)).all()
        
        for doc in documents:
            print(f"Document: {doc.filename}")
            print(f"  Current Stage: {doc.current_stage}")
            print(f"  Stage Status: {doc.stage_status}")
            print(f"  Overall Status: {doc.overall_status}")
            print(f"  Upload Status: {doc.stages.get('upload', {}).get('status', 'N/A')}")
            print(f"  Parse Status: {doc.stages.get('parse', {}).get('status', 'N/A')}")
            print(f"  Metadata (clean): {doc.metadata_dict}")
            print("-" * 60)
        
        print("\n3. TESTING STATUS UPDATES:")
        # Test updating status
        doc = documents[0]
        print(f"Testing status update on: {doc.filename}")
        print(f"  Before: current_stage={doc.current_stage}, stage_status={doc.stage_status}")
        
        # Update parse stage to running
        doc.update_stage_status("parse", "running", 
                               started_at="2025-06-09T15:00:00Z", 
                               attempts=1)
        session.add(doc)
        session.commit()
        session.refresh(doc)
        
        print(f"  After update: current_stage={doc.current_stage}, stage_status={doc.stage_status}")
        print(f"  Parse stage: {doc.stages.get('parse', {})}")

if __name__ == "__main__":
    verify_new_status_structure() 