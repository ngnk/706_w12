#!/bin/bash

# IoT Streaming System - Quick Start Script
# This script helps you start all components in the correct order

echo "🌡️  IoT Environmental Monitoring System - Startup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# Start Docker infrastructure
echo "🐳 Starting Docker infrastructure (Kafka + PostgreSQL)..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start Docker services${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker services started${NC}"
echo ""

# Wait for services to be ready
echo "⏳ Waiting for services to be ready (30 seconds)..."
sleep 30

# Check if services are healthy
echo "🔍 Checking service health..."
docker-compose ps

echo ""
echo "✅ Infrastructure is ready!"
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Install Python dependencies (if not already installed):"
echo "   ${YELLOW}pip install -r requirements.txt${NC}"
echo ""
echo "2. Start the components in separate terminal windows:"
echo ""
echo "   Terminal 1 - Producer (sensor data generator):"
echo "   ${YELLOW}python producer.py${NC}"
echo ""
echo "   Terminal 2 - Consumer (data storage):"
echo "   ${YELLOW}python consumer.py${NC}"
echo ""
echo "   Terminal 3 - Stream Processor (windowed aggregations):"
echo "   ${YELLOW}python stream_processor.py${NC}"
echo ""
echo "   Terminal 4 - ML Detector (anomaly detection):"
echo "   ${YELLOW}python ml_detector.py${NC}"
echo ""
echo "   Terminal 5 - Dashboard (visualization):"
echo "   ${YELLOW}streamlit run dashboard.py${NC}"
echo ""
echo "3. Access the dashboard at: ${GREEN}http://localhost:8501${NC}"
echo ""
echo "To stop the infrastructure:"
echo "   ${YELLOW}docker-compose down${NC}"
echo ""
