#!/bin/bash

echo "=========================================="
echo " Professional Download Manager Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "\n${YELLOW}[1/5] Updating system packages...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &> /dev/null; then
        brew update
    else
        echo -e "${RED}Homebrew not found. Please install it first.${NC}"
        exit 1
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
    elif command -v yum &> /dev/null; then
        sudo yum update
    elif command -v dnf &> /dev/null; then
        sudo dnf update
    fi
fi

echo -e "\n${YELLOW}[2/5] Installing Python dependencies...${NC}"
python3 -m pip install --upgrade pip setuptools wheel
pip3 install -r requirements.txt

echo -e "\n${YELLOW}[3/5] Installing external tools...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS with Homebrew
    brew install aria2 wget curl ffmpeg yt-dlp
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y aria2 wget curl ffmpeg
        pip3 install yt-dlp
    elif command -v yum &> /dev/null; then
        sudo yum install -y aria2 wget curl ffmpeg
        pip3 install yt-dlp
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y aria2 wget curl ffmpeg
        pip3 install yt-dlp
    fi
fi

echo -e "\n${YELLOW}[4/5] Installing optional dependencies...${NC}"
# Install system-specific packages
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y python3-magic libmagic1
    fi
fi

echo -e "\n${YELLOW}[5/5] Verifying installation...${NC}"
python3 -c "import flask, requests, telegram; print('✅ Core packages installed')" 2>/dev/null || echo -e "${RED}❌ Core packages failed${NC}"
python3 -c "import yt_dlp; print('✅ yt-dlp installed')" 2>/dev/null || echo -e "${RED}❌ yt-dlp failed${NC}"
python3 -c "from PIL import Image; print('✅ Pillow installed')" 2>/dev/null || echo -e "${RED}❌ Pillow failed${NC}"

# Test external tools
echo -e "\n${YELLOW}Testing external tools:${NC}"
command -v aria2c >/dev/null 2>&1 && echo -e "${GREEN}✅ aria2${NC}" || echo -e "${RED}❌ aria2${NC}"
command -v wget >/dev/null 2>&1 && echo -e "${GREEN}✅ wget${NC}" || echo -e "${RED}❌ wget${NC}"
command -v curl >/dev/null 2>&1 && echo -e "${GREEN}✅ curl${NC}" || echo -e "${RED}❌ curl${NC}"
command -v ffmpeg >/dev/null 2>&1 && echo -e "${GREEN}✅ ffmpeg${NC}" || echo -e "${RED}❌ ffmpeg${NC}"
command -v yt-dlp >/dev/null 2>&1 && echo -e "${GREEN}✅ yt-dlp${NC}" || echo -e "${RED}❌ yt-dlp${NC}"

echo -e "\n${GREEN}=========================================="
echo " Installation Complete!"
echo "=========================================="
echo -e "${NC}"
echo "To start the application:"
echo "python3 main.py"
echo ""
