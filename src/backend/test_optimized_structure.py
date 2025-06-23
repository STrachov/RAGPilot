#!/usr/bin/env python3
"""
Test script to verify the optimized document structure
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.db import engine
from sqlmodel import Session, select
from app.core.models.document import Document
import json

def test_optimized_structure():
    """Test the optimized document structure"""
    
    print("🔍 Testing Optimized Document Structure")
    print("=" * 50)
    
    with Session(engine) as session:
        # Get all documents
        documents = session.exec(select(Document)).all()
        
        print(f"📊 Found {len(documents)} documents in database")
        
        for i, doc in enumerate(documents[:3]):  # Test first 3 documents
            print(f"\n📄 Document {i+1}: {doc.filename}")
            print(f"   ID: {doc.id}")
            print(f"   Binary Hash: {doc.binary_hash}")
            print(f"   Page Count: {doc.page_count}")
            
            # Test status structure
            status = doc.status_dict
            print(f"   Status Structure: ✅" if "stages" in status else "❌ Missing stages")
            
            if "stages" in status:
                stages = status["stages"]
                for stage_name, stage_data in stages.items():
                    stage_status = stage_data.get("status", "unknown")
                    print(f"     {stage_name}: {stage_status}")
            
            # Test metadata structure  
            metadata = doc.metadata_dict
            print(f"   Metadata: {json.dumps(metadata, indent=2) if metadata else 'None'}")
            
            # Test computed properties
            print(f"   Current Stage (computed): {doc.current_stage}")
            print(f"   Stage Status (computed): {doc.stage_status}")
            print(f"   Overall Status (computed): {doc.overall_status}")
            
            # Test parse config access
            try:
                parse_config = doc.parse_config
                print(f"   Parse Config Access: ✅")
            except Exception as e:
                print(f"   Parse Config Access: ❌ {e}")
            
            # Test ragparser task id access
            task_id = doc.ragparser_task_id
            print(f"   RAGParser Task ID: {task_id if task_id else 'None'}")
            
            print("-" * 30)
    
    print("\n✅ Optimized structure test completed!")

if __name__ == "__main__":
    test_optimized_structure() 