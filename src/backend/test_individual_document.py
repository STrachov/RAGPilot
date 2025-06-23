#!/usr/bin/env python3
"""
Test script to check individual document endpoint
"""

import requests
import json
from sqlmodel import Session, select
from app.core.db import engine
from app.core.models.document import Document

def test_individual_document_endpoint():
    """Test the individual document endpoint"""
    
    # Get a document ID from the database
    with Session(engine) as session:
        document = session.exec(select(Document)).first()
        if not document:
            print("No documents found in database")
            return
        
        document_id = document.id
        print(f"Testing endpoint for document: {document.filename}")
        print(f"Document ID: {document_id}")
        
        # Test the API endpoint
        url = f"http://localhost:8080/api/v1/documents/{document_id}"
        print(f"Testing URL: {url}")
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Success! Response data:")
                print(json.dumps(data, indent=2))
                
                # Check if status is properly parsed
                if 'status' in data:
                    status = data['status']
                    print(f"\n✅ Status type: {type(status)}")
                    if isinstance(status, dict):
                        print(f"✅ Status is parsed object with keys: {list(status.keys())}")
                    else:
                        print(f"❌ Status is still a string: {status}")
                        
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_individual_document_endpoint() 