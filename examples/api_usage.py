"""
Knowledge Graph Extraction API - Python Usage Example

This example demonstrates how to use the API from Python code.

Author: AI Assistant
Date: 2025-11-10
"""

import requests
import json
import time
from pathlib import Path


# Configuration
API_BASE_URL = "http://localhost:8000"
SAMPLE_FILE = "path/to/your/document.json"  # Replace with your file


def health_check():
    """Check API health status"""
    print("🔍 Checking API health...")
    response = requests.get(f"{API_BASE_URL}/api/v1/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API is healthy")
        print(f"   Version: {data['version']}")
        print(f"   LLM Available: {data['llm_available']}")
        return True
    else:
        print(f"❌ API health check failed: {response.status_code}")
        return False


def extract_sync(file_path: str, chunk_size: int = 512, max_workers: int = 3):
    """
    Extract knowledge graph (synchronous for small files).
    
    Args:
        file_path: Path to JSON document
        chunk_size: Chunk size parameter
        max_workers: Max parallel workers
        
    Returns:
        dict: Extraction result
    """
    print(f"\n📄 Uploading file: {file_path}")
    
    with open(file_path, 'rb') as f:
        files = {'file': ('document.json', f, 'application/json')}
        params = {
            'chunk_size': chunk_size,
            'max_workers': max_workers
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/extract",
            files=files,
            params=params
        )
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print("✅ Extraction completed synchronously")
            result = data['data']
            print(f"   Raw Entities: {len(result['raw_graph']['entities'])}")
            print(f"   Raw Relations: {len(result['raw_graph']['relations'])}")
            print(f"   Aligned Entities: {len(result['aligned_graph']['entities'])}")
            print(f"   Aligned Relations: {len(result['aligned_graph']['relations'])}")
            return result
        else:
            print(f"❌ Extraction failed: {data.get('error')}")
            return None
    
    elif response.status_code == 202:
        # Async task submitted
        data = response.json()
        task_id = data['data']['task_id']
        print(f"📋 Task submitted asynchronously: {task_id}")
        return poll_task_status(task_id)
    
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
        return None


def poll_task_status(task_id: str, max_wait: int = 600):
    """
    Poll task status until completion.
    
    Args:
        task_id: Task ID to poll
        max_wait: Maximum wait time in seconds
        
    Returns:
        dict: Task result if completed
    """
    print(f"⏳ Polling task status: {task_id}")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"{API_BASE_URL}/api/v1/tasks/{task_id}")
        
        if response.status_code == 200:
            data = response.json()
            task_data = data['data']
            status = task_data['status']
            progress = task_data.get('progress', 0)
            
            print(f"   Status: {status} | Progress: {progress:.1f}%")
            
            if status == "completed":
                print("✅ Task completed!")
                result = task_data['result']
                print(f"   Raw Entities: {len(result['raw_graph']['entities'])}")
                print(f"   Aligned Entities: {len(result['aligned_graph']['entities'])}")
                return result
            
            elif status == "failed":
                error = task_data.get('error', 'Unknown error')
                print(f"❌ Task failed: {error}")
                return None
            
            # Wait before next poll
            time.sleep(2)
        
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return None
    
    print(f"⏰ Timeout: Task did not complete within {max_wait} seconds")
    return None


def save_results(result: dict, output_dir: str = "./api_results"):
    """Save extraction results to files"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save raw graph
    raw_path = output_path / "result_raw.json"
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(result['raw_graph'], f, ensure_ascii=False, indent=2)
    print(f"💾 Saved raw graph to: {raw_path}")
    
    # Save aligned graph
    aligned_path = output_path / "result_aligned.json"
    with open(aligned_path, 'w', encoding='utf-8') as f:
        json.dump(result['aligned_graph'], f, ensure_ascii=False, indent=2)
    print(f"💾 Saved aligned graph to: {aligned_path}")
    
    # Save summary
    summary_path = output_path / "summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(result['summary'], f, ensure_ascii=False, indent=2)
    print(f"💾 Saved summary to: {summary_path}")


def main():
    """Main example function"""
    print("=" * 60)
    print("Knowledge Graph Extraction API - Python Example")
    print("=" * 60)
    
    # Step 1: Health check
    if not health_check():
        print("\n⚠️  API is not available. Please start the server first.")
        print("   Run: python api.py")
        return
    
    # Step 2: Extract knowledge graph
    # Replace SAMPLE_FILE with your actual file path
    if not Path(SAMPLE_FILE).exists():
        print(f"\n⚠️  Sample file not found: {SAMPLE_FILE}")
        print("   Please update SAMPLE_FILE variable with your document path.")
        return
    
    result = extract_sync(
        SAMPLE_FILE,
        chunk_size=512,
        max_workers=3
    )
    
    if result:
        # Step 3: Save results
        print("\n💾 Saving results...")
        save_results(result)
        
        print("\n✅ Complete! Results saved to ./api_results/")
    else:
        print("\n❌ Extraction failed")


if __name__ == "__main__":
    main()
