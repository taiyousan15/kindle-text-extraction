#!/bin/bash

# Kindle OCR Frontend Setup Script
# This script sets up the Next.js frontend for the Kindle OCR system

set -e

echo "========================================="
echo "Kindle OCR Frontend Setup"
echo "========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "Error: Node.js version must be 18 or higher"
    echo "Current version: $(node -v)"
    exit 1
fi

echo "✓ Node.js $(node -v) detected"
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

echo "✓ npm $(npm -v) detected"
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")"

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local file..."
    cat > .env.local << EOF
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Application Configuration
NEXT_PUBLIC_APP_NAME="Kindle OCR"
NEXT_PUBLIC_APP_VERSION="2.0.0"
EOF
    echo "✓ .env.local created"
else
    echo "✓ .env.local already exists"
fi

echo ""
echo "Installing dependencies..."
npm install

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the FastAPI backend:"
echo "   cd .. && uvicorn app.main:app --reload"
echo ""
echo "2. Start the frontend development server:"
echo "   npm run dev"
echo ""
echo "3. Open http://localhost:3000 in your browser"
echo ""
echo "For production build:"
echo "   npm run build"
echo "   npm run start"
echo ""
