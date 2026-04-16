"""Bicep template generation for Azure IoT resources.

Generates Bicep modules for IoT Hub, Device Provisioning Service,
Event Hubs, Stream Analytics, Azure Data Explorer, storage accounts,
and complete IoT landing zone stacks.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class IotBicepService:
    """Service for generating Bicep templates for IoT resources."""

    def generate_iot_hub(self, config: dict) -> str:
        """Generate Bicep template for Azure IoT Hub.

        Args:
            config: Dict with keys: name, location, sku_name,
                sku_capacity.

        Returns:
            Bicep template string for the IoT Hub resource.
        """
        name = config.get("name", "iotHub")
        location = config.get("location", "eastus")
        sku_name = config.get("sku_name", "S1")
        sku_capacity = config.get("sku_capacity", 1)

        return f"""// Azure IoT Hub for device connectivity and management
param location string = '{location}'
param iotHubName string = '{name}'

resource iotHub 'Microsoft.Devices/IotHubs@2023-06-30' = {{
  name: iotHubName
  location: location
  sku: {{
    name: '{sku_name}'
    capacity: {sku_capacity}
  }}
  properties: {{
    eventHubEndpoints: {{
      events: {{
        retentionTimeInDays: 1
        partitionCount: 4
      }}
    }}
    routing: {{
      routes: [
        {{
          name: 'default'
          source: 'DeviceMessages'
          condition: 'true'
          endpointNames: [
            'events'
          ]
          isEnabled: true
        }}
      ]
    }}
    cloudToDevice: {{
      defaultTtlAsIso8601: 'PT1H'
      maxDeliveryCount: 10
    }}
  }}
}}

output iotHubId string = iotHub.id
output iotHubName string = iotHub.name
output eventHubEndpoint string = iotHub.properties.eventHubEndpoints.events.endpoint
"""

    def generate_dps(self, config: dict) -> str:
        """Generate Bicep template for Device Provisioning Service.

        Args:
            config: Dict with keys: name, location, iot_hub_name.

        Returns:
            Bicep template string for the DPS resource.
        """
        name = config.get("name", "iotDps")
        location = config.get("location", "eastus")

        return f"""// Azure IoT Hub Device Provisioning Service
param location string = '{location}'
param dpsName string = '{name}'

resource dps 'Microsoft.Devices/provisioningServices@2022-12-12' = {{
  name: dpsName
  location: location
  sku: {{
    name: 'S1'
    capacity: 1
  }}
  properties: {{
    allocationPolicy: 'Hashed'
  }}
}}

output dpsId string = dps.id
output dpsName string = dps.name
output serviceOperationsHostName string = dps.properties.serviceOperationsHostName
"""

    def generate_event_hub(self, config: dict) -> str:
        """Generate Bicep template for Azure Event Hubs namespace.

        Args:
            config: Dict with keys: name, location, sku,
                throughput_units, partition_count.

        Returns:
            Bicep template string for Event Hubs resources.
        """
        name = config.get("name", "iotEventHub")
        location = config.get("location", "eastus")
        sku = config.get("sku", "Standard")
        throughput = config.get("throughput_units", 1)
        partitions = config.get("partition_count", 4)

        return f"""// Azure Event Hubs for high-throughput IoT telemetry
param location string = '{location}'
param namespaceName string = '{name}'

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' = {{
  name: namespaceName
  location: location
  sku: {{
    name: '{sku}'
    tier: '{sku}'
    capacity: {throughput}
  }}
}}

resource telemetryHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {{
  parent: eventHubNamespace
  name: 'telemetry'
  properties: {{
    partitionCount: {partitions}
    messageRetentionInDays: 7
  }}
}}

output namespaceId string = eventHubNamespace.id
output telemetryHubName string = telemetryHub.name
"""

    def generate_stream_analytics(self, config: dict) -> str:
        """Generate Bicep template for Azure Stream Analytics job.

        Args:
            config: Dict with keys: name, location, streaming_units.

        Returns:
            Bicep template string for Stream Analytics job.
        """
        name = config.get("name", "iotStreamJob")
        location = config.get("location", "eastus")
        streaming_units = config.get("streaming_units", 3)

        return f"""// Azure Stream Analytics for real-time IoT processing
param location string = '{location}'
param jobName string = '{name}'

resource streamJob 'Microsoft.StreamAnalytics/streamingjobs@2021-10-01-preview' = {{
  name: jobName
  location: location
  properties: {{
    sku: {{
      name: 'StandardV2'
    }}
    outputErrorPolicy: 'Stop'
    eventsOutOfOrderPolicy: 'Adjust'
    eventsOutOfOrderMaxDelayInSeconds: 5
    eventsLateArrivalMaxDelayInSeconds: 16
    compatibilityLevel: '1.2'
    transformation: {{
      name: 'IoTTransformation'
      properties: {{
        streamingUnits: {streaming_units}
        query: 'SELECT * INTO [output] FROM [input]'
      }}
    }}
  }}
}}

output jobId string = streamJob.id
output jobName string = streamJob.name
"""

    def generate_storage(self, config: dict) -> str:
        """Generate Bicep template for IoT storage account.

        Args:
            config: Dict with keys: name, location, sku,
                enable_cold_tier.

        Returns:
            Bicep template string for the storage account.
        """
        name = config.get("name", "iotstorage")
        location = config.get("location", "eastus")
        sku = config.get("sku", "Standard_LRS")
        enable_cold = config.get("enable_cold_tier", False)

        cold_section = ""
        if enable_cold:
            cold_section = """
  resource lifecyclePolicy 'managementPolicies' = {
    name: 'default'
    properties: {
      policy: {
        rules: [
          {
            name: 'moveToCool'
            type: 'Lifecycle'
            definition: {
              actions: {
                baseBlob: {
                  tierToCool: {
                    daysAfterModificationGreaterThan: 30
                  }
                  tierToArchive: {
                    daysAfterModificationGreaterThan: 90
                  }
                }
              }
              filters: {
                blobTypes: ['blockBlob']
                prefixMatch: ['telemetry/']
              }
            }
          }
        ]
      }
    }
  }"""

        return f"""// Azure Storage for IoT telemetry data
param location string = '{location}'
param storageName string = '{name}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {{
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: {{
    name: '{sku}'
  }}
  properties: {{
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }}
{cold_section}
}}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {{
  parent: storageAccount
  name: 'default'
}}

resource telemetryContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {{
  parent: blobService
  name: 'telemetry'
  properties: {{
    publicAccess: 'None'
  }}
}}

output storageId string = storageAccount.id
output storageName string = storageAccount.name
"""

    def generate_adx(self, config: dict) -> str:
        """Generate Bicep template for Azure Data Explorer cluster.

        Args:
            config: Dict with keys: name, location, sku_name,
                sku_tier, sku_capacity.

        Returns:
            Bicep template string for the ADX cluster.
        """
        name = config.get("name", "iotadx")
        location = config.get("location", "eastus")
        sku_name = config.get("sku_name", "Standard_E2ads_v5")
        sku_tier = config.get("sku_tier", "Standard")
        capacity = config.get("sku_capacity", 2)

        return f"""// Azure Data Explorer for IoT time series analytics
param location string = '{location}'
param clusterName string = '{name}'

resource adxCluster 'Microsoft.Kusto/clusters@2023-08-15' = {{
  name: clusterName
  location: location
  sku: {{
    name: '{sku_name}'
    tier: '{sku_tier}'
    capacity: {capacity}
  }}
  properties: {{
    enableStreamingIngest: true
    enableAutoStop: true
  }}
}}

resource telemetryDb 'Microsoft.Kusto/clusters/databases@2023-08-15' = {{
  parent: adxCluster
  name: 'telemetry'
  location: location
  kind: 'ReadWrite'
  properties: {{
    softDeletePeriod: 'P365D'
    hotCachePeriod: 'P31D'
  }}
}}

output clusterId string = adxCluster.id
output clusterUri string = adxCluster.properties.uri
output databaseName string = telemetryDb.name
"""

    def generate_full_iot_stack(self, config: dict) -> str:
        """Generate a complete IoT landing zone Bicep template.

        Args:
            config: Dict with keys: name_prefix, location,
                iot_hub_sku, include_dps, include_edge,
                include_event_hubs, include_stream_analytics,
                include_adx, include_cold_storage.

        Returns:
            Combined Bicep template string for the full stack.
        """
        prefix = config.get("name_prefix", "iot")
        location = config.get("location", "eastus")
        hub_sku = config.get("iot_hub_sku", "S1")
        include_dps = config.get("include_dps", True)
        include_eh = config.get("include_event_hubs", False)
        include_sa = config.get("include_stream_analytics", False)
        include_adx = config.get("include_adx", False)
        include_cold = config.get("include_cold_storage", False)

        sections: list[str] = []

        sections.append(f"""// IoT Landing Zone — full stack
// Generated by OnRamp IoT Accelerator
targetScope = 'resourceGroup'

param location string = '{location}'
param namePrefix string = '{prefix}'
""")

        # IoT Hub
        sections.append(f"""// ── IoT Hub ──────────────────────────────────────────────────────────────
resource iotHub 'Microsoft.Devices/IotHubs@2023-06-30' = {{
  name: '${{namePrefix}}-hub'
  location: location
  sku: {{
    name: '{hub_sku}'
    capacity: 1
  }}
  properties: {{
    eventHubEndpoints: {{
      events: {{
        retentionTimeInDays: 1
        partitionCount: 4
      }}
    }}
    routing: {{
      routes: [
        {{
          name: 'default'
          source: 'DeviceMessages'
          condition: 'true'
          endpointNames: ['events']
          isEnabled: true
        }}
      ]
    }}
  }}
}}
""")

        # Storage
        sections.append("""// ── Storage ──────────────────────────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${namePrefix}store'
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}
""")

        # DPS
        if include_dps:
            sections.append("""// ── Device Provisioning Service ──────────────────────────────────────────
resource dps 'Microsoft.Devices/provisioningServices@2022-12-12' = {
  name: '${namePrefix}-dps'
  location: location
  sku: {
    name: 'S1'
    capacity: 1
  }
  properties: {
    allocationPolicy: 'Hashed'
    iotHubs: [
      {
        connectionString: 'HostName=${iotHub.name}.azure-devices.net'
        location: location
      }
    ]
  }
}
""")

        # Event Hubs
        if include_eh:
            sections.append("""// ── Event Hubs ───────────────────────────────────────────────────────────
resource eventHubNs 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: '${namePrefix}-eh'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
}

resource telemetryEh 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  parent: eventHubNs
  name: 'telemetry'
  properties: {
    partitionCount: 4
    messageRetentionInDays: 7
  }
}
""")

        # Stream Analytics
        if include_sa:
            sections.append("""// ── Stream Analytics ─────────────────────────────────────────────────────
resource streamJob 'Microsoft.StreamAnalytics/streamingjobs@2021-10-01-preview' = {
  name: '${namePrefix}-asa'
  location: location
  properties: {
    sku: {
      name: 'StandardV2'
    }
    outputErrorPolicy: 'Stop'
    eventsOutOfOrderPolicy: 'Adjust'
    compatibilityLevel: '1.2'
  }
}
""")

        # ADX
        if include_adx:
            sections.append("""// ── Azure Data Explorer ──────────────────────────────────────────────────
resource adxCluster 'Microsoft.Kusto/clusters@2023-08-15' = {
  name: '${namePrefix}adx'
  location: location
  sku: {
    name: 'Standard_E2ads_v5'
    tier: 'Standard'
    capacity: 2
  }
  properties: {
    enableStreamingIngest: true
    enableAutoStop: true
  }
}

resource adxDb 'Microsoft.Kusto/clusters/databases@2023-08-15' = {
  parent: adxCluster
  name: 'telemetry'
  location: location
  kind: 'ReadWrite'
  properties: {
    softDeletePeriod: 'P365D'
    hotCachePeriod: 'P31D'
  }
}
""")

        # Cold storage lifecycle
        if include_cold:
            sections.append("""// ── Cold Storage Lifecycle ────────────────────────────────────────────────
resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  name: 'default'
  parent: storageAccount
  properties: {
    policy: {
      rules: [
        {
          name: 'tierToCold'
          type: 'Lifecycle'
          definition: {
            actions: {
              baseBlob: {
                tierToCool: {
                  daysAfterModificationGreaterThan: 30
                }
                tierToArchive: {
                  daysAfterModificationGreaterThan: 90
                }
              }
            }
            filters: {
              blobTypes: ['blockBlob']
              prefixMatch: ['telemetry/']
            }
          }
        }
      ]
    }
  }
}
""")

        # Outputs
        sections.append("""// ── Outputs ──────────────────────────────────────────────────────────────
output iotHubId string = iotHub.id
output iotHubName string = iotHub.name
output storageAccountId string = storageAccount.id
""")

        return "\n".join(sections)


iot_bicep_service = IotBicepService()
