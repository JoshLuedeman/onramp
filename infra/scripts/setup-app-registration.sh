#!/bin/bash
# OnRamp App Registration Setup Script
# Runs as a deploymentScript in ARM to create or validate an Entra ID app registration.
# Uses the deploying user's identity (via managedIdentity or user-assigned identity).

set -e

APP_NAME="${APP_NAME:-OnRamp}"
REDIRECT_URI="${REDIRECT_URI:-https://onramp.azurewebsites.net}"
CREATE_APP="${CREATE_APP:-true}"
EXISTING_CLIENT_ID="${EXISTING_CLIENT_ID:-}"

echo "=== OnRamp App Registration Setup ==="
echo "App Name: $APP_NAME"
echo "Redirect URI: $REDIRECT_URI"
echo "Create New: $CREATE_APP"

# Install az cli extensions if needed
az extension add --name account 2>/dev/null || true

if [ "$CREATE_APP" = "false" ] && [ -n "$EXISTING_CLIENT_ID" ]; then
    echo "Using existing app registration: $EXISTING_CLIENT_ID"
    
    # Validate it exists
    APP_INFO=$(az ad app show --id "$EXISTING_CLIENT_ID" -o json 2>/dev/null) || {
        echo "ERROR: App registration $EXISTING_CLIENT_ID not found"
        exit 1
    }
    
    CLIENT_ID="$EXISTING_CLIENT_ID"
    APP_OBJECT_ID=$(echo "$APP_INFO" | jq -r '.id')
    echo "Validated existing app: $(echo "$APP_INFO" | jq -r '.displayName')"
else
    echo "Creating new app registration..."
    
    # Create the app registration
    APP_INFO=$(az ad app create \
        --display-name "$APP_NAME" \
        --sign-in-audience "AzureADMyOrg" \
        --web-redirect-uris "$REDIRECT_URI" "${REDIRECT_URI}/auth/callback" "http://localhost:5173" "http://localhost:5173/auth/callback" \
        --enable-id-token-issuance true \
        --enable-access-token-issuance true \
        -o json)
    
    CLIENT_ID=$(echo "$APP_INFO" | jq -r '.appId')
    APP_OBJECT_ID=$(echo "$APP_INFO" | jq -r '.id')
    
    echo "Created app registration:"
    echo "  Display Name: $APP_NAME"
    echo "  Client ID: $CLIENT_ID"
    echo "  Object ID: $APP_OBJECT_ID"
    
    # Create a service principal for the app
    SP_INFO=$(az ad sp create --id "$CLIENT_ID" -o json 2>/dev/null) || {
        echo "Service principal may already exist, continuing..."
    }
    
    # Add required API permissions
    # Microsoft Graph - User.Read (delegated)
    echo "Adding Microsoft Graph User.Read permission..."
    az ad app permission add \
        --id "$CLIENT_ID" \
        --api 00000003-0000-0000-c000-000000000000 \
        --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope \
        2>/dev/null || echo "Permission may already exist"
    
    # Azure Service Management - user_impersonation (delegated)
    echo "Adding Azure Management user_impersonation permission..."
    az ad app permission add \
        --id "$CLIENT_ID" \
        --api 797f4846-ba00-4fd7-ba43-dac1f8f63013 \
        --api-permissions 41094075-9dad-400e-a0bd-54e686782033=Scope \
        2>/dev/null || echo "Permission may already exist"
    
    # Create a client secret
    echo "Creating client secret..."
    SECRET_INFO=$(az ad app credential reset \
        --id "$CLIENT_ID" \
        --display-name "OnRamp Deployment" \
        --years 2 \
        -o json)
    
    CLIENT_SECRET=$(echo "$SECRET_INFO" | jq -r '.password')
    
    echo ""
    echo "============================================"
    echo "  App Registration Created Successfully"
    echo "============================================"
    echo ""
    echo "  Client ID:     $CLIENT_ID"
    echo "  Tenant ID:     $(az account show --query tenantId -o tsv)"
    echo ""
    echo "  Required Permissions (grant admin consent in portal):"
    echo "    - Microsoft Graph: User.Read"
    echo "    - Azure Service Management: user_impersonation"
    echo ""
    echo "  The app registration allows OnRamp to:"
    echo "    1. Sign in users with their Entra ID identity"
    echo "    2. Read basic user profile information"
    echo "    3. Deploy Azure resources on behalf of the user"
    echo ""
    echo "  Redirect URIs configured:"
    echo "    - $REDIRECT_URI"
    echo "    - ${REDIRECT_URI}/auth/callback"
    echo "    - http://localhost:5173 (development)"
    echo "    - http://localhost:5173/auth/callback (development)"
    echo ""
fi

# Get tenant ID
TENANT_ID=$(az account show --query tenantId -o tsv)

# Output results as JSON for ARM template to consume
cat <<EOF > $AZ_SCRIPTS_OUTPUT_DIRECTORY/result.json
{
    "clientId": "$CLIENT_ID",
    "tenantId": "$TENANT_ID",
    "appObjectId": "${APP_OBJECT_ID:-}",
    "clientSecret": "${CLIENT_SECRET:-}"
}
EOF

echo "Setup complete. Results written for deployment pipeline."
