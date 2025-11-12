"""
Quick API Test - Verify API can start and basic endpoints work

Run this test before starting the full API server.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all imports work"""
    print("Testing imports...")
    try:
        from api_models import (
            ExtractRequest, ExtractResponse, TaskStatus,
            HealthResponse, ErrorResponse
        )
        from text_pipline import TextKnowledgeGraphPipeline
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def test_models():
    """Test that Pydantic models work"""
    print("\nTesting Pydantic models...")
    try:
        from api_models import ExtractRequest, HealthResponse
        
        # Test ExtractRequest
        req = ExtractRequest(
            chunk_size=512,
            max_workers=3,
            temperature=0.3
        )
        print(f"✅ ExtractRequest: {req.chunk_size}, {req.max_workers}")
        
        # Test HealthResponse
        health = HealthResponse(
            status="healthy",
            version="1.3.0",
            llm_available=True,
            timestamp="2025-11-10T12:00:00Z"
        )
        print(f"✅ HealthResponse: {health.status}")
        
        return True
    except Exception as e:
        print(f"❌ Model error: {e}")
        return False


def test_env_config():
    """Test environment configuration"""
    print("\nTesting configuration...")
    try:
        import os
        import dotenv
        dotenv.load_dotenv()
        
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if api_key:
            print(f"✅ DASHSCOPE_API_KEY configured (length: {len(api_key)})")
        else:
            print("⚠️  DASHSCOPE_API_KEY not set (API will not work)")
        
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("FastAPI API Quick Test")
    print("=" * 60)
    
    results = []
    results.append(test_imports())
    results.append(test_models())
    results.append(test_env_config())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All tests passed! API is ready to start.")
        print("\nTo start the API:")
        print("  Windows: run_api.bat")
        print("  Linux/Mac: python -m uvicorn api:app --reload")
    else:
        print("❌ Some tests failed. Please fix issues before starting API.")
    print("=" * 60)


if __name__ == "__main__":
    main()
