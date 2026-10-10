#!/bin/bash

# Keycloak One-Time Setup Script
# This script performs mandatory one-time setup tasks for Keycloak.
# It should be run once when setting up a new cluster, then commented out in docker-compose.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration from environment variables
KEYCLOAK_URL="${KEYCLOAK_BASE_URL:-http://keycloak:8080}"
KEYCLOAK_HEALTH_URL="${KEYCLOAK_HEALTH_URL:-http://keycloak:9000/health/ready}"
KEYCLOAK_ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

print_info "Starting Keycloak one-time setup..."
print_info "Keycloak URL: $KEYCLOAK_URL"
print_info "Admin Username: $KEYCLOAK_ADMIN_USERNAME"
echo ""

# Wait for Keycloak to be ready
print_info "Waiting for Keycloak to be ready..."
MAX_RETRIES=60
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "${KEYCLOAK_HEALTH_URL}" >/dev/null 2>&1; then
        print_success "Keycloak is ready"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        print_error "Keycloak health check timeout after $((MAX_RETRIES * 2)) seconds"
        exit 1
    fi
    sleep 2
done

# Step 1: Update master realm SSL requirement to 'none' (for development)
print_info "Step 1: Updating master realm SSL requirement to 'none'..."
python3 <<EOF
import asyncio
import httpx
import os
import sys

async def update_master_realm_ssl():
    keycloak_url = os.getenv("KEYCLOAK_BASE_URL", "http://keycloak:8080")
    admin_username = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get admin token
            token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": admin_username,
                    "password": admin_password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            
            # Get current realm configuration
            realm_url = f"{keycloak_url}/admin/realms/master"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            realm_response = await client.get(realm_url, headers=headers)
            realm_response.raise_for_status()
            realm_data = realm_response.json()
            
            # Update SSL requirement if needed
            if realm_data.get("sslRequired") != "none":
                realm_data["sslRequired"] = "none"
                update_response = await client.put(
                    realm_url,
                    headers=headers,
                    json=realm_data
                )
                update_response.raise_for_status()
                print("✅ Master realm SSL requirement updated to 'none'")
            else:
                print("✅ Master realm SSL requirement already set to 'none'")
    except Exception as e:
        print(f"❌ Error updating master realm SSL: {e}")
        sys.exit(1)

asyncio.run(update_master_realm_ssl())
EOF

if [ $? -eq 0 ]; then
    print_success "Master realm SSL configuration completed"
else
    print_error "Failed to update master realm SSL"
    exit 1
fi

# Step 2: Configure Google Identity Provider (if credentials are provided)
if [ -n "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ]; then
    echo ""
    print_info "Step 2: Configuring Google Identity Provider for tenant-default realm..."
    python3 <<EOF
import asyncio
import httpx
import os
import sys

async def configure_google_idp():
    keycloak_url = os.getenv("KEYCLOAK_BASE_URL", "http://keycloak:8080")
    admin_username = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    realm_name = "tenant-default"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get admin token
            token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": admin_username,
                    "password": admin_password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Check if realm exists, create if not (basic realm creation)
            realm_url = f"{keycloak_url}/admin/realms/{realm_name}"
            realm_check = await client.get(realm_url, headers=headers)
            if realm_check.status_code == 404:
                print(f"Creating {realm_name} realm...")
                create_realm_response = await client.post(
                    f"{keycloak_url}/admin/realms",
                    headers=headers,
                    json={
                        "realm": realm_name,
                        "enabled": True,
                        "displayName": "Personal Accounts Realm",
                        "sslRequired": "none"
                    }
                )
                if create_realm_response.status_code not in [201, 409]:
                    create_realm_response.raise_for_status()
            
            # Check if Google IdP already exists
            idp_url = f"{keycloak_url}/admin/realms/{realm_name}/identity-provider/instances/google"
            idp_check = await client.get(idp_url, headers=headers)
            
            idp_config = {
                "alias": "google",
                "providerId": "google",
                "enabled": True,
                "config": {
                    "clientId": google_client_id,
                    "clientSecret": google_client_secret
                }
            }
            
            if idp_check.status_code == 200:
                # Update existing IdP
                update_response = await client.put(idp_url, headers=headers, json=idp_config)
                if update_response.status_code in [200, 204]:
                    print("✅ Google Identity Provider updated successfully")
                else:
                    update_response.raise_for_status()
            else:
                # Create new IdP
                create_response = await client.post(
                    f"{keycloak_url}/admin/realms/{realm_name}/identity-provider/instances",
                    headers=headers,
                    json=idp_config
                )
                if create_response.status_code in [201, 409]:
                    print("✅ Google Identity Provider created successfully")
                else:
                    create_response.raise_for_status()
    except Exception as e:
        print(f"⚠️  Warning: Failed to configure Google Identity Provider: {e}")
        print("   This is not critical - you can configure it later manually")
        # Don't exit with error for optional Google IdP setup

asyncio.run(configure_google_idp())
EOF
    if [ $? -eq 0 ]; then
        print_success "Google Identity Provider configuration completed"
    else
        print_warning "Google Identity Provider configuration had issues (non-critical)"
    fi
else
    echo ""
    print_info "Step 2: Skipping Google Identity Provider configuration (credentials not provided)"
    print_info "To configure later, set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables"
fi

echo ""
print_success "Keycloak one-time setup completed successfully!"
print_info "This service can now be commented out in docker-compose.yml"
echo ""

