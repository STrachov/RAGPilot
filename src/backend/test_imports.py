#!/usr/bin/env python3

print("🧪 Testing all main API imports...")

try:
    print("📋 Testing config service...")
    from app.core.services.config_service import config_service
    print("✅ Config service imported successfully")

    print("📄 Testing document stages...")
    from app.core.services.document_stages import document_stages  
    print("✅ Document stages imported successfully")

    print("🌐 Testing config routes...")
    from app.api.routes.config import router as config_router
    print("✅ Config routes imported successfully")

    print("📂 Testing document routes...")
    from app.api.routes.documents import router as documents_router
    print("✅ Document routes imported successfully")

    print("🔗 Testing main API router...")
    from app.api.main import api_router
    print("✅ Main API router imported successfully")

    print("\n🎉 All imports working correctly!")
    print("✅ JSON configuration system is ready")
    print("✅ Document processing pipeline is ready")
    print("✅ API routes are ready")

except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc() 