targetScope = 'managementGroup'

@description('Management group ID for policy scope')
param managementGroupId string

@description('Allowed Azure regions')
param allowedLocations array = [
  'eastus'
  'eastus2'
  'westus2'
  'centralus'
]

resource allowedLocationsPolicy 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'policy-allowed-locations'
  properties: {
    displayName: 'Allowed locations'
    description: 'Restricts resources to approved Azure regions'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c'
    parameters: {
      listOfAllowedLocations: {
        value: allowedLocations
      }
    }
    enforcementMode: 'Default'
  }
}

resource requireTagPolicy 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'policy-require-env-tag'
  properties: {
    displayName: 'Require Environment tag on resources'
    description: 'Denies resource creation without the Environment tag'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/871b6d14-10aa-478d-b590-94f262e6899c'
    parameters: {
      tagName: {
        value: 'Environment'
      }
    }
    enforcementMode: 'Default'
  }
}

resource secureTransferPolicy 'Microsoft.Authorization/policyAssignments@2024-04-01' = {
  name: 'policy-secure-transfer'
  properties: {
    displayName: 'Require secure transfer for storage accounts'
    description: 'Audits storage accounts that do not require secure transfer'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/404c3081-a854-4457-ae30-26a93ef643f9'
    enforcementMode: 'Default'
  }
}
