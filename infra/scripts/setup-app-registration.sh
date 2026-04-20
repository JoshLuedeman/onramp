#!/bin/bash
# OnRamp App Registration Setup Script
# Runs as a deploymentScript in ARM to create or validate an Entra ID app registration.
# Uses the bootstrap managed identity (requires Microsoft Graph Application.ReadWrite.All).

set -euo pipefail

APP_NAME="${APP_NAME:-OnRamp}"
REDIRECT_URI="${REDIRECT_URI:-https://onramp.azurewebsites.net}"
CREATE_APP="${CREATE_APP:-true}"
EXISTING_CLIENT_ID="${EXISTING_CLIENT_ID:-}"
EXISTING_CLIENT_SECRET="${EXISTING_CLIENT_SECRET:-}"
OWNER_GROUP_OBJECT_ID="${OWNER_GROUP_OBJECT_ID:-}"
KV_NAME="${KV_NAME:-}"

echo "=== OnRamp App Registration Setup ==="
echo "App Name: $APP_NAME"
echo "Redirect URI: $REDIRECT_URI"
echo "Create New: $CREATE_APP"
echo "Owner Group: ${OWNER_GROUP_OBJECT_ID:-<not set>}"

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

    # Store existing client secret in Key Vault if provided
    if [ -n "$KV_NAME" ] && [ -n "$EXISTING_CLIENT_SECRET" ]; then
        az keyvault secret set --vault-name "$KV_NAME" --name entra-client-secret \
            --value "$EXISTING_CLIENT_SECRET" --output none
        echo "Stored existing client secret in Key Vault"
    fi
else
    echo "Creating new app registration..."

    # Verify we have Graph permissions before proceeding
    az ad app list --top 1 -o none 2>/dev/null || {
        echo "ERROR: Bootstrap identity lacks Microsoft Graph permissions."
        echo "Grant Application.ReadWrite.All to the bootstrap managed identity,"
        echo "or set createAppRegistration=false and provide an existing app registration."
        exit 1
    }

    # Create the app registration
    APP_INFO=$(az ad app create \
        --display-name "$APP_NAME" \
        --sign-in-audience "AzureADMyOrg" \
        --web-redirect-uris "$REDIRECT_URI" "${REDIRECT_URI}/auth/callback" "http://localhost:5173" "http://localhost:5173/auth/callback" \
        --enable-id-token-issuance true \
        --enable-access-token-issuance false \
        -o json)

    CLIENT_ID=$(echo "$APP_INFO" | jq -r '.appId')
    APP_OBJECT_ID=$(echo "$APP_INFO" | jq -r '.id')

    echo "Created app registration:"
    echo "  Display Name: $APP_NAME"
    echo "  Client ID: $CLIENT_ID"
    echo "  Object ID: $APP_OBJECT_ID"

    # Configure the exposed API with identifier URI and access_as_user scope
    echo "Configuring exposed API scope..."
    az rest --method PATCH --url "https://graph.microsoft.com/v1.0/applications/$APP_OBJECT_ID" \
        --headers "Content-Type=application/json" \
        --body "{
            \"identifierUris\": [\"api://$CLIENT_ID\"],
            \"api\": {
                \"oauth2PermissionScopes\": [{
                    \"id\": \"$(cat /proc/sys/kernel/random/uuid)\",
                    \"adminConsentDisplayName\": \"Access OnRamp as user\",
                    \"adminConsentDescription\": \"Allow the application to access OnRamp on behalf of the signed-in user.\",
                    \"userConsentDisplayName\": \"Access OnRamp as user\",
                    \"userConsentDescription\": \"Allow the application to access OnRamp on your behalf.\",
                    \"isEnabled\": true,
                    \"type\": \"User\",
                    \"value\": \"access_as_user\"
                }]
            }
        }" --output none 2>/dev/null || echo "Exposed API scope may already exist"
    echo "  Configured api://$CLIENT_ID/access_as_user scope"

    # Create a service principal for the app
    SP_INFO=$(az ad sp create --id "$CLIENT_ID" -o json 2>/dev/null) || {
        echo "Service principal may already exist, continuing..."
        SP_INFO=$(az ad sp show --id "$CLIENT_ID" -o json 2>/dev/null) || true
    }
    SP_OBJECT_ID=$(echo "$SP_INFO" | jq -r '.id // empty')

    # Assign roles at subscription scope
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    if [ -n "$SP_OBJECT_ID" ]; then
        echo "Assigning Contributor role to service principal..."
        az role assignment create \
            --assignee-object-id "$SP_OBJECT_ID" \
            --assignee-principal-type ServicePrincipal \
            --role "Contributor" \
            --scope "/subscriptions/$SUBSCRIPTION_ID" \
            2>/dev/null || echo "Role assignment may already exist"

        echo "Assigning User Access Administrator role..."
        az role assignment create \
            --assignee-object-id "$SP_OBJECT_ID" \
            --assignee-principal-type ServicePrincipal \
            --role "User Access Administrator" \
            --scope "/subscriptions/$SUBSCRIPTION_ID" \
            2>/dev/null || echo "Role assignment may already exist"

        echo "  Assigned Contributor and User Access Administrator roles"
    else
        echo "  Could not determine SP object ID — assign roles manually"
    fi

    # Add required API permissions
    echo "Adding Microsoft Graph User.Read permission..."
    az ad app permission add \
        --id "$CLIENT_ID" \
        --api 00000003-0000-0000-c000-000000000000 \
        --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope \
        2>/dev/null || echo "Permission may already exist"

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

    # Store client secret in Key Vault
    if [ -n "$KV_NAME" ]; then
        az keyvault secret set --vault-name "$KV_NAME" --name entra-client-secret \
            --value "$CLIENT_SECRET" --output none
        echo "Stored client secret in Key Vault"
    fi

    echo ""
    echo "  App Registration Created: $CLIENT_ID"
    echo "  Exposed API: api://$CLIENT_ID/access_as_user"
    echo "  Grant admin consent in Entra ID > App registrations for:"
    echo "    - Microsoft Graph: User.Read"
    echo "    - Azure Service Management: user_impersonation"
    echo ""
fi

# Get tenant ID
TENANT_ID=$(az account show --query tenantId -o tsv)

# Store client ID and tenant ID in Key Vault
if [ -n "$KV_NAME" ]; then
    az keyvault secret set --vault-name "$KV_NAME" --name entra-client-id \
        --value "$CLIENT_ID" --output none
    az keyvault secret set --vault-name "$KV_NAME" --name entra-tenant-id \
        --value "$TENANT_ID" --output none
    echo "Stored client ID and tenant ID in Key Vault"
fi

# Output results as JSON for ARM template to consume
cat <<EOF > $AZ_SCRIPTS_OUTPUT_DIRECTORY/result.json
{
    "clientId": "$CLIENT_ID",
    "tenantId": "$TENANT_ID",
    "appObjectId": "${APP_OBJECT_ID:-}"
}
EOF

echo "=== App Registration Setup Complete ==="
