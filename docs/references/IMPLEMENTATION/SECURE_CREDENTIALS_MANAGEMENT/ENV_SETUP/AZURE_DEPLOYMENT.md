# Azure Deployment Guide

This guide covers deploying the Stock Alerter application to Azure Container Instances using Azure Key Vault for credential management.

## Prerequisites

- Azure CLI installed and configured
- Active Azure subscription
- Docker image built and pushed to Azure Container Registry (or Docker Hub)

## Step 1: Create Azure Key Vault

```bash
# Set variables
RESOURCE_GROUP="stock-alerter-rg"
KEYVAULT_NAME="stock-alerter-kv"
LOCATION="eastus"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Create Key Vault
az keyvault create \
  --name $KEYVAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --enable-rbac-authorization
```

## Step 2: Add Secrets to Key Vault

Azure Key Vault uses hyphens instead of underscores. The SecretsLoader automatically converts between them.

```bash
# Email credentials
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "email-sender" \
  --value "your-email@gmail.com"

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "email-app-password" \
  --value "xxxx xxxx xxxx xxxx"

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "email-sender-display-name" \
  --value "Stock Alerter (No-Reply)"

# Twilio credentials (if using SMS)
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "twilio-account-sid" \
  --value "ACxxxxxxxxxxxxxxxxxx"

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "twilio-auth-token" \
  --value "your_auth_token_here"
```

## Step 3: Create Managed Identity

```bash
# Create user-assigned managed identity
az identity create \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-identity

# Get identity ID
IDENTITY_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-identity \
  --query id -o tsv)

IDENTITY_PRINCIPAL_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-identity \
  --query principalId -o tsv)
```

## Step 4: Grant Key Vault Access

```bash
# Grant the identity permission to read secrets from Key Vault
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --scope $(az keyvault show --name $KEYVAULT_NAME --query id -o tsv)
```

## Step 5: Deploy to Container Instances

```bash
# Get Key Vault URL
KEYVAULT_URL="https://${KEYVAULT_NAME}.vault.azure.net/"

# Deploy container instance
az container create \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-app \
  --image stock-alerter:latest \
  --cpu 1 \
  --memory 1 \
  --environment-variables \
    EMAIL_ENABLED="true" \
    EMAIL_RECEIVERS="recipient@example.com" \
    EMAIL_BCC_RECEIVERS="admin@example.com" \
    NTFY_ENABLED="false" \
    TWILIO_ENABLED="false" \
    AZURE_KEYVAULT_URL="$KEYVAULT_URL" \
  --assign-identity $IDENTITY_ID \
  --ports 5000 \
  --restart-policy OnFailure
```

## Step 6: Verify Deployment

```bash
# Get container status
az container show \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-app \
  --query instanceView.state

# Get logs
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-app

# Get IP address
az container show \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-app \
  --query ipAddress.ip
```

## Step 7: Update Secrets

To update a secret without redeploying:

```bash
# Update the secret in Key Vault
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "email-app-password" \
  --value "new_password_here"

# Restart the container instance
az container restart \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-app
```

## Step 8: Cleanup

```bash
# Delete container instance
az container delete \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter-app \
  --yes

# Delete resource group (deletes all resources)
az group delete \
  --name $RESOURCE_GROUP \
  --yes
```

## Troubleshooting

### Secret Not Found Error

If you see errors like "Secret 'email-app-password' not found in Azure Key Vault":

1. Verify the secret exists:
   ```bash
   az keyvault secret list --vault-name $KEYVAULT_NAME
   ```

2. Check the secret name format (should use hyphens, not underscores)

3. Verify the managed identity has access:
   ```bash
   az role assignment list \
     --assignee $IDENTITY_PRINCIPAL_ID \
     --scope $(az keyvault show --name $KEYVAULT_NAME --query id -o tsv)
   ```

### Authentication Error

If authentication fails:

1. Verify AZURE_KEYVAULT_URL is set correctly
2. Ensure managed identity is assigned to the container
3. Check role assignments for the identity
4. Verify Key Vault network rules allow access

### Application Not Starting

1. Check container logs:
   ```bash
   az container logs --resource-group $RESOURCE_GROUP --name stock-alerter-app
   ```

2. Verify environment variables are passed correctly

3. Check application for any startup errors

## Security Best Practices

1. **Use Managed Identities**: Never store credentials in container configuration
2. **Role-Based Access Control (RBAC)**: Grant only necessary permissions
3. **Network Security**: Use VNet integration to restrict access
4. **Audit Logging**: Enable Key Vault audit logs
5. **Secret Rotation**: Implement automatic secret rotation
6. **Monitoring**: Set up alerts for failed authentication attempts

## Cost Optimization

- Use shared Key Vault for multiple applications
- Clean up unused resources
- Monitor container CPU/memory usage and adjust as needed
- Consider App Service or Kubernetes for production workloads

## References

- [Azure Key Vault Documentation](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Azure Container Instances Documentation](https://learn.microsoft.com/en-us/azure/container-instances/)
- [Azure Managed Identities](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
