#!/usr/bin/env python3
"""
Test script for dynamic pipeline endpoints
Tests the new pipeline functionality to ensure frontend integration works
"""

import asyncio
import requests
import json
from datetime import datetime
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000/api"
TEST_DOCUMENT_ID = "test-doc-123"  # You'll need to replace with a real document ID

class PipelineEndpointTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_get_available_pipelines(self) -> Dict[str, Any]:
        """Test the GET /documents/pipelines endpoint"""
        print("🔍 Testing: GET /documents/pipelines")
        
        try:
            response = self.session.get(f"{self.base_url}/documents/pipelines")
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Success: Found {len(data)} available pipelines")
            
            for name, pipeline in data.items():
                print(f"   📋 Pipeline: {name}")
                print(f"      Description: {pipeline.get('description', 'N/A')}")
                print(f"      Stages: {len(pipeline.get('stages', []))}")
                print(f"      Estimated duration: {pipeline.get('estimated_duration_minutes', 'N/A')} min")
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed: {e}")
            return {}
    
    def test_get_available_stages(self) -> Dict[str, Any]:
        """Test the GET /documents/stages endpoint"""
        print("\n🔍 Testing: GET /documents/stages")
        
        try:
            response = self.session.get(f"{self.base_url}/documents/stages")
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Success: Found {len(data)} available stages")
            
            for name, stage in data.items():
                print(f"   ⚙️  Stage: {name}")
                print(f"      Description: {stage.get('description', 'N/A')}")
                print(f"      Function: {stage.get('function_name', 'N/A')}")
                print(f"      Dependencies: {stage.get('dependencies', [])}")
                print(f"      Timeout: {stage.get('default_timeout_seconds', 'N/A')}s")
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed: {e}")
            return {}
    
    def test_execute_pipeline(self, document_id: str, pipeline_name: str = "standard_rag") -> bool:
        """Test the POST /documents/{id}/pipelines/{name}/execute endpoint"""
        print(f"\n🔍 Testing: POST /documents/{document_id}/pipelines/{pipeline_name}/execute")
        
        # Test with custom configuration
        config_overrides = {
            "parse": {
                "parser_type": "docling",
                "do_ocr": True,
                "extract_tables": True
            },
            "chunk": {
                "chunk_size": 800,
                "chunk_overlap": 150
            },
            "index": {
                "model_name": "text-embedding-3-small",
                "use_vector_db": True
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/documents/{document_id}/pipelines/{pipeline_name}/execute",
                json={"config_overrides": config_overrides}
            )
            
            if response.status_code == 404:
                print(f"⚠️  Document {document_id} not found - this is expected for test document ID")
                return False
            elif response.status_code == 400:
                print(f"⚠️  Bad request - possibly invalid pipeline name or config")
                return False
                
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Success: Pipeline execution started")
            print(f"   Message: {data.get('message', 'N/A')}")
            print(f"   Pipeline: {data.get('pipeline_name', 'N/A')}")
            print(f"   Document ID: {data.get('document_id', 'N/A')}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"   Error details: {error_data}")
                except:
                    print(f"   Raw response: {e.response.text}")
            return False
    
    def test_get_pipeline_status(self, document_id: str, pipeline_name: str = "standard_rag") -> Dict[str, Any]:
        """Test the GET /documents/{id}/pipelines/{name}/status endpoint"""
        print(f"\n🔍 Testing: GET /documents/{document_id}/pipelines/{pipeline_name}/status")
        
        try:
            response = self.session.get(
                f"{self.base_url}/documents/{document_id}/pipelines/{pipeline_name}/status"
            )
            
            if response.status_code == 404:
                print(f"⚠️  Document {document_id} not found - this is expected for test document ID")
                return {}
                
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Success: Retrieved pipeline status")
            print(f"   Pipeline: {data.get('pipeline_name', 'N/A')}")
            print(f"   Overall Status: {data.get('overall_status', 'N/A')}")
            print(f"   Progress: {data.get('progress', 0)}%")
            
            stages = data.get('stages', {})
            print(f"   Stages ({len(stages)}):")
            for stage_name, stage_info in stages.items():
                status = stage_info.get('status', 'unknown')
                print(f"      {stage_name}: {status}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed: {e}")
            return {}
    
    def test_all_endpoints(self, document_id: str = None):
        """Test all pipeline endpoints"""
        print("🚀 Testing Dynamic Pipeline API Endpoints")
        print("=" * 50)
        
        # Test pipeline and stage discovery
        pipelines = self.test_get_available_pipelines()
        stages = self.test_get_available_stages()
        
        if not pipelines or not stages:
            print("\n❌ Basic endpoints failed - check if backend is running")
            return
        
        # If we have a valid document ID, test execution endpoints
        if document_id and document_id != "test-doc-123":
            print(f"\n📄 Testing with document ID: {document_id}")
            
            # Test pipeline execution
            self.test_execute_pipeline(document_id, "parse_only")  # Use parse_only for safety
            
            # Test status retrieval
            self.test_get_pipeline_status(document_id, "parse_only")
        else:
            print(f"\n⚠️  Skipping execution tests - no valid document ID provided")
            print(f"   To test execution, run: python {__file__} <document_id>")
        
        print("\n🎉 Pipeline endpoint testing completed!")
        
        # Summary
        print("\n📊 SUMMARY:")
        print(f"   ✅ Available Pipelines: {len(pipelines)}")
        print(f"   ✅ Available Stages: {len(stages)}")
        print("   🔧 Ready for frontend integration!")

def main():
    import sys
    
    # Check if server is running
    tester = PipelineEndpointTester(BASE_URL)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"🟢 Backend server is running at {BASE_URL}")
    except requests.exceptions.RequestException:
        print(f"🔴 Backend server is not responding at {BASE_URL}")
        print("   Make sure the FastAPI server is running with: uvicorn app.main:app --reload")
        return
    
    # Get document ID from command line if provided
    document_id = sys.argv[1] if len(sys.argv) > 1 else TEST_DOCUMENT_ID
    
    # Run tests
    tester.test_all_endpoints(document_id)

if __name__ == "__main__":
    main() 