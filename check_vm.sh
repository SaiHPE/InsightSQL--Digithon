#!/bin/bash

echo "=========================================="
echo "    VM GPU & LLM Context Gathering Script "
echo "=========================================="
echo ""

echo "--- 1. GPU & VRAM Status ---"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free --format=csv
    echo ""
    echo "Detailed Process VRAM Usage:"
    nvidia-smi pmon -c 1
else
    echo "nvidia-smi not found. No NVIDIA GPU detected or drivers missing."
fi
echo ""

echo "--- 2. Docker Containers (Looking for LLM services) ---"
if command -v docker &> /dev/null; then
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"
else
    echo "Docker is not installed or not running."
fi
echo ""

echo "--- 3. Local Ollama Models ---"
if command -v ollama &> /dev/null; then
    ollama list
else
    echo "Ollama command line tool not found."
fi
echo ""

echo "--- 4. Probing Common Local API Endpoints ---"

# Probe vLLM / Standard OpenAI compatible port (8000)
echo "-> Probing http://localhost:8000/v1/models (vLLM / Triton / FastAPI)..."
RESPONSE_8000=$(curl -s -f --max-time 2 http://localhost:8000/v1/models)
if [ $? -eq 0 ]; then
    echo "$RESPONSE_8000" | grep -o '"id":"[^"]*"' | sed 's/"id"://g' | sed 's/"//g' | awk '{print "   Found model: "$0}'
else
    echo "   Endpoint unreachable or returned no models."
fi

# Probe standard Ollama API port
echo "-> Probing http://localhost:11434/api/tags (Ollama)..."
RESPONSE_11434=$(curl -s -f --max-time 2 http://localhost:11434/api/tags)
if [ $? -eq 0 ]; then
    echo "$RESPONSE_11434" | grep -o '"name":"[^"]*"' | sed 's/"name"://g' | sed 's/"//g' | awk '{print "   Found model: "$0}'
else
    echo "   Endpoint unreachable or returned no models."
fi

# Probe Text Generation Inference (TGI) or other common port (8080)
echo "-> Probing http://localhost:8080/info (TGI / vLLM alternate)..."
curl -s -f --max-time 2 http://localhost:8080/info || echo "   Endpoint unreachable."
echo ""

echo "=========================================="
echo " Gathering complete."
echo "=========================================="
