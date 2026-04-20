#!/bin/bash
# setup-sql-entra-user.sh
#
# Called by the Bicep deployment script resource in sql.bicep.
# Creates a contained database user for the application managed identity,
# grants it the necessary roles, then switches the SQL AD admin to the
# Entra group.
#
# Required environment variables (set by Bicep):
#   SQL_SERVER_FQDN          — e.g. sql-onramp-dev.database.windows.net
#   DATABASE_NAME            — e.g. sqldb-onramp-dev
#   SQL_SERVER_NAME          — e.g. sql-onramp-dev
#   RESOURCE_GROUP           — e.g. rg-onramp-dev
#   APP_IDENTITY_NAME        — display name of the app managed identity
#   APP_IDENTITY_CLIENT_ID   — client (application) ID of the app managed identity
#   ADMIN_GROUP_NAME         — display name of the Entra admin group
#   ADMIN_GROUP_OID          — object ID of the Entra admin group

set -euo pipefail

echo "=== OnRamp SQL Entra Auth Setup ==="
echo "Server: $SQL_SERVER_FQDN"
echo "Database: $DATABASE_NAME"
echo "App identity: $APP_IDENTITY_NAME ($APP_IDENTITY_CLIENT_ID)"
echo "Admin group: $ADMIN_GROUP_NAME ($ADMIN_GROUP_OID)"

# ── Step 1: Install ODBC driver and pyodbc ──────────────────────────────────
echo "Installing ODBC driver..."
apt-get update -qq
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
  > /etc/apt/sources.list.d/mssql-release.list
apt-get update -qq
ACCEPT_EULA=Y apt-get install -y -qq msodbcsql18 unixodbc-dev > /dev/null 2>&1
pip install -q pyodbc

# ── Step 2: Get access token for Azure SQL ──────────────────────────────────
echo "Acquiring access token for Azure SQL..."
TOKEN=$(az account get-access-token --resource https://database.windows.net --query accessToken -o tsv)

# ── Step 3: Create contained database user for app identity ─────────────────
echo "Creating contained database user for app identity..."
python3 << 'PYEOF'
import os
import struct
import sys

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc not available", file=sys.stderr)
    sys.exit(1)

token = os.environ["TOKEN"]
server = os.environ["SQL_SERVER_FQDN"]
database = os.environ["DATABASE_NAME"]
identity_name = os.environ["APP_IDENTITY_NAME"]
identity_client_id = os.environ["APP_IDENTITY_CLIENT_ID"]

# Pack the access token for ODBC SQL_COPT_SS_ACCESS_TOKEN (1256)
token_bytes = token.encode("utf-16-le")
token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

conn_str = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:{server},1433;"
    f"Database={database};"
    f"Encrypt=yes;TrustServerCertificate=no"
)

print(f"Connecting to {server}/{database}...")
conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
cursor = conn.cursor()

# Use SID-based user creation to avoid needing Directory Readers on the SQL server.
# The SID is the binary representation of the managed identity's client (application) ID.
sql = f"""
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'{identity_name}')
BEGIN
    DECLARE @sid VARBINARY(16) = CAST(CAST('{identity_client_id}' AS UNIQUEIDENTIFIER) AS VARBINARY(16));
    DECLARE @sql NVARCHAR(MAX) = N'CREATE USER [{identity_name}] WITH SID = '
        + '0x' + CONVERT(VARCHAR(MAX), @sid, 2) + ', TYPE = E';
    EXEC sp_executesql @sql;
    PRINT 'Created user [{identity_name}]';
END
ELSE
    PRINT 'User [{identity_name}] already exists';
"""
cursor.execute(sql)
conn.commit()

# Grant database roles
for role in ("db_datareader", "db_datawriter", "db_ddladmin"):
    cursor.execute(f"ALTER ROLE {role} ADD MEMBER [{identity_name}]")
    print(f"  Granted {role}")
conn.commit()

cursor.close()
conn.close()
print("Database user setup complete.")
PYEOF

export TOKEN  # make available to the Python heredoc

# ── Step 4: Switch SQL admin to the Entra group ────────────────────────────
echo "Switching SQL AD admin to Entra group: $ADMIN_GROUP_NAME..."
az sql server ad-admin create \
  --server-name "$SQL_SERVER_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --display-name "$ADMIN_GROUP_NAME" \
  --object-id "$ADMIN_GROUP_OID" \
  --output none

echo "=== SQL Entra auth setup complete ==="
echo "  Admin: $ADMIN_GROUP_NAME (group)"
echo "  App user: $APP_IDENTITY_NAME (managed identity)"
