#!/bin/bash
# deploy.sh
# Deployment script
# Called by GitHub Actions Workflow via SSH

set -e

# ========== VARIABLES ==========
APP_DIR="/home/ubuntu/finvestigate"
DATA_DIR="/home/ubuntu/finvestigate-data"
BRANCH="${1:-develop}"

echo "=========================================="
echo "🚀 Finvestigate Deployment Starting..."
echo "📌 Branch: ${BRANCH}"
echo "=========================================="

# ========== STEP 1: CREATE PERSISTENT DIRECTORIES ==========
echo ""
echo "📁 Step 1: Creating persistent data directories..."
mkdir -p ${DATA_DIR}/postgres
mkdir -p ${DATA_DIR}/uploads
echo "✅ Directories ready"

# ========== STEP 2: SETUP APP DIRECTORY ==========
echo ""
echo "📂 Step 2: Setting up app directory..."
if [ ! -d "${APP_DIR}/.git" ]; then
    echo "📥 Not a git repo. Cloning..."
    # Backup .env.production if it exists
    if [ -f "${APP_DIR}/.env.production" ]; then
        cp ${APP_DIR}/.env.production /tmp/.env.production.backup
    fi
    # Remove and clone fresh
    rm -rf ${APP_DIR}
    git clone https://github.com/mananurrehman/finvestigate.git ${APP_DIR}
    # Restore .env.production
    if [ -f "/tmp/.env.production.backup" ]; then
        cp /tmp/.env.production.backup ${APP_DIR}/.env.production
        rm /tmp/.env.production.backup
    fi
fi
cd ${APP_DIR}
echo "✅ In ${APP_DIR}"

# ========== STEP 3: PULL LATEST CODE ==========
echo ""
echo "📥 Step 3: Pulling latest code..."
git fetch origin
git checkout ${BRANCH}
git pull origin ${BRANCH}
echo "✅ Code updated to latest ${BRANCH}"

# ========== STEP 4: STOP OLD CONTAINERS ==========
echo ""
echo "🛑 Step 4: Stopping existing containers..."
docker compose down --remove-orphans || true
echo "✅ Old containers stopped"

# ========== STEP 5: BUILD AND START ==========
echo ""
echo "🔨 Step 5: Building and starting containers..."
docker compose up -d --build
echo "✅ Containers started"

# ========== STEP 6: VERIFY ==========
echo ""
echo "🔍 Step 6: Waiting for containers to be healthy..."
sleep 30

echo ""
echo "Container Status:"
docker compose ps

echo ""
echo "=========================================="
echo "🎉 Finvestigate Deployed Successfully!"
echo "🌐 Access: http://$(curl -s ifconfig.me):5000"
echo "=========================================="