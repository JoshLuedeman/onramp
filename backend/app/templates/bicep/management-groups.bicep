targetScope = 'tenant'

@description('Root management group display name')
param rootDisplayName string = 'Tenant Root Group'

@description('Management group hierarchy definition')
param hierarchy object

resource rootMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-root'
  properties: {
    displayName: rootDisplayName
  }
}

resource platformMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-platform'
  properties: {
    displayName: 'Platform'
    details: {
      parent: {
        id: rootMg.id
      }
    }
  }
}

resource identityMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-identity'
  properties: {
    displayName: 'Identity'
    details: {
      parent: {
        id: platformMg.id
      }
    }
  }
}

resource managementMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-management'
  properties: {
    displayName: 'Management'
    details: {
      parent: {
        id: platformMg.id
      }
    }
  }
}

resource connectivityMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-connectivity'
  properties: {
    displayName: 'Connectivity'
    details: {
      parent: {
        id: platformMg.id
      }
    }
  }
}

resource landingZonesMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-landing-zones'
  properties: {
    displayName: 'Landing Zones'
    details: {
      parent: {
        id: rootMg.id
      }
    }
  }
}

resource corpMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-corp'
  properties: {
    displayName: 'Corp'
    details: {
      parent: {
        id: landingZonesMg.id
      }
    }
  }
}

resource onlineMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-online'
  properties: {
    displayName: 'Online'
    details: {
      parent: {
        id: landingZonesMg.id
      }
    }
  }
}

resource sandboxMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-sandbox'
  properties: {
    displayName: 'Sandbox'
    details: {
      parent: {
        id: rootMg.id
      }
    }
  }
}

resource decommissionedMg 'Microsoft.Management/managementGroups@2021-04-01' = {
  name: 'mg-decommissioned'
  properties: {
    displayName: 'Decommissioned'
    details: {
      parent: {
        id: rootMg.id
      }
    }
  }
}
