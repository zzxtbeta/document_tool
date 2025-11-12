#!/bin/bash
# Knowledge Graph Extraction API - cURL Examples
# 
# Usage: bash curl_examples.sh
# Note: Requires curl and jq (optional for pretty JSON)

API_URL="http://localhost:8000"
SAMPLE_FILE="path/to/your/document.json"  # Replace with your file

echo "============================================"
echo "Knowledge Graph Extraction API - cURL Examples"
echo "============================================"
echo ""

# -----------------------------------------------------------------------------
# 1. Health Check
# -----------------------------------------------------------------------------
echo "1️⃣  Health Check"
echo "   GET /api/v1/health"
echo ""

curl -X GET "${API_URL}/api/v1/health" \
  -H "Accept: application/json" \
  | jq '.'  # Remove '| jq' if jq is not installed

echo ""
echo ""

# -----------------------------------------------------------------------------
# 2. Extract Knowledge Graph (Synchronous - Small File)
# -----------------------------------------------------------------------------
echo "2️⃣  Extract Knowledge Graph (Sync)"
echo "   POST /api/v1/extract"
echo ""

curl -X POST "${API_URL}/api/v1/extract" \
  -H "Accept: application/json" \
  -F "file=@${SAMPLE_FILE}" \
  -F "chunk_size=512" \
  -F "max_workers=3" \
  -F "temperature=0.3" \
  -F "parallel=true" \
  | jq '.metadata, .data.summary'  # Show only metadata and summary

echo ""
echo ""

# -----------------------------------------------------------------------------
# 3. Extract with Custom Parameters
# -----------------------------------------------------------------------------
echo "3️⃣  Extract with Custom Parameters"
echo "   POST /api/v1/extract (chunk_size=1024, max_workers=8)"
echo ""

curl -X POST "${API_URL}/api/v1/extract" \
  -H "Accept: application/json" \
  -F "file=@${SAMPLE_FILE}" \
  -F "chunk_size=1024" \
  -F "max_workers=8" \
  -F "temperature=0.2" \
  | jq '.metadata'

echo ""
echo ""

# -----------------------------------------------------------------------------
# 4. Async Extraction (Large File)
# -----------------------------------------------------------------------------
echo "4️⃣  Async Extraction (for large files)"
echo "   POST /api/v1/extract"
echo ""

# This will return a task_id if file is large
RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/extract" \
  -F "file=@${SAMPLE_FILE}" \
  -F "chunk_size=512")

echo "$RESPONSE" | jq '.'

# Extract task_id if async
TASK_ID=$(echo "$RESPONSE" | jq -r '.data.task_id // empty')

if [ -n "$TASK_ID" ]; then
  echo ""
  echo "   Task ID: $TASK_ID"
  
  # -----------------------------------------------------------------------------
  # 5. Check Task Status
  # -----------------------------------------------------------------------------
  echo ""
  echo "5️⃣  Check Task Status"
  echo "   GET /api/v1/tasks/${TASK_ID}"
  echo ""
  
  # Poll task status (check every 2 seconds, max 10 times)
  for i in {1..10}; do
    echo "   Checking status (attempt $i)..."
    
    STATUS_RESPONSE=$(curl -s -X GET "${API_URL}/api/v1/tasks/${TASK_ID}")
    echo "$STATUS_RESPONSE" | jq '.data.status, .data.progress'
    
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.data.status')
    
    if [ "$STATUS" = "completed" ]; then
      echo ""
      echo "   ✅ Task completed!"
      echo "$STATUS_RESPONSE" | jq '.data.summary'
      break
    elif [ "$STATUS" = "failed" ]; then
      echo ""
      echo "   ❌ Task failed!"
      echo "$STATUS_RESPONSE" | jq '.data.error'
      break
    fi
    
    sleep 2
  done
fi

echo ""
echo "============================================"
echo "Examples Complete!"
echo "============================================"
echo ""
echo "📚 API Documentation: ${API_URL}/docs"
echo "🔄 ReDoc: ${API_URL}/redoc"
