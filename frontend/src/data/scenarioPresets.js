/**
 * Core Hackathon Scenario Presets for 1-Click Evaluation in NetCoop AI.
 */

export const SCENARIO_PRESETS = [
  {
    id: 'normal_network',
    label: '1. Normal Network Operation',
    tag: 'Healthy',
    tone: 'green',
    description: 'Low utilization, zero packet loss, healthy router and reachable switch on active link.',
    data: {
      performanceSamples: [
        {
          device_id: 'RTR-N1',
          interface_id: 'xe-0/0/0',
          latency_ms: 18,
          jitter_ms: 2,
          packet_loss_pct: 0,
          throughput_mbps: 220,
          link_utilization_pct: 32,
        },
      ],
      infrastructureSamples: [
        {
          device_id: 'RTR-N1',
          interface_id: 'xe-0/0/0',
          cpu_utilization_pct: 28,
          memory_utilization_pct: 46,
          interface_errors: 0,
          egress_queue_drops: 0,
          device_status: 'online',
        },
      ],
      devices: [
        { device_id: 'RTR-N1', segment_id: 'core', reachability: 'reachable' },
        { device_id: 'SW-N1', segment_id: 'core', reachability: 'reachable' },
      ],
      links: [
        { link_id: 'L-N1', source_device_id: 'RTR-N1', target_device_id: 'SW-N1', status: 'up' },
      ],
    },
  },
  {
    id: 'link_congestion',
    label: '2. Link Congestion & Queue Drops',
    tag: 'Congestion',
    tone: 'amber',
    description: 'High 96% link utilization, 185ms latency, packet loss, and 18 egress queue drops.',
    data: {
      performanceSamples: [
        {
          device_id: 'RTR-C2',
          interface_id: 'xe-0/0/1',
          latency_ms: 185,
          jitter_ms: 42,
          packet_loss_pct: 2.4,
          throughput_mbps: 890,
          link_utilization_pct: 96,
        },
      ],
      infrastructureSamples: [
        {
          device_id: 'RTR-C2',
          interface_id: 'xe-0/0/1',
          cpu_utilization_pct: 54,
          memory_utilization_pct: 61,
          interface_errors: 0,
          egress_queue_drops: 18,
          device_status: 'online',
        },
      ],
      devices: [
        { device_id: 'RTR-C2', segment_id: 'branch-east', reachability: 'reachable' },
        { device_id: 'SW-C2', segment_id: 'branch-east', reachability: 'reachable' },
      ],
      links: [
        { link_id: 'L-C2', source_device_id: 'RTR-C2', target_device_id: 'SW-C2', status: 'up' },
      ],
    },
  },
  {
    id: 'weak_wifi_signal',
    label: '3. Weak Wi-Fi Signal (RF Attenuation)',
    tag: 'Wireless',
    tone: 'blue',
    description: 'Poor Wi-Fi RSSI (-84 dBm) coinciding with 5.8% packet loss and elevated latency on AP-W3.',
    data: {
      performanceSamples: [
        {
          device_id: 'AP-W3',
          interface_id: 'wlan0',
          latency_ms: 195,
          jitter_ms: 45,
          packet_loss_pct: 5.8,
          throughput_mbps: 25,
          link_utilization_pct: 40,
        },
      ],
      infrastructureSamples: [
        {
          device_id: 'AP-W3',
          interface_id: 'wlan0',
          cpu_utilization_pct: 32,
          memory_utilization_pct: 41,
          interface_errors: 0,
          egress_queue_drops: 0,
          device_status: 'degraded',
        },
      ],
      devices: [
        { device_id: 'AP-W3', segment_id: 'wireless-branch', reachability: 'reachable' },
        { device_id: 'STA-W3', segment_id: 'wireless-branch', reachability: 'reachable' },
      ],
      links: [
        { link_id: 'L-W3', source_device_id: 'AP-W3', target_device_id: 'STA-W3', status: 'up' },
      ],
    },
  },
  {
    id: 'ethernet_interface_fault',
    label: '4. Physical Ethernet Interface Fault',
    tag: 'Hardware',
    tone: 'purple',
    description: '72 CRC / framing interface errors with packet loss on SW-E4 while queue drops remain 0.',
    data: {
      performanceSamples: [
        {
          device_id: 'SW-E4',
          interface_id: 'eth1',
          latency_ms: 22,
          jitter_ms: 3,
          packet_loss_pct: 4.6,
          throughput_mbps: 450,
          link_utilization_pct: 20,
        },
      ],
      infrastructureSamples: [
        {
          device_id: 'SW-E4',
          interface_id: 'eth1',
          cpu_utilization_pct: 26,
          memory_utilization_pct: 38,
          interface_errors: 72,
          egress_queue_drops: 0,
          device_status: 'online',
        },
      ],
      devices: [
        { device_id: 'SW-E4', segment_id: 'distribution', reachability: 'reachable' },
        { device_id: 'RTR-E4', segment_id: 'distribution', reachability: 'reachable' },
      ],
      links: [
        { link_id: 'L-E4', source_device_id: 'SW-E4', target_device_id: 'RTR-E4', status: 'up' },
      ],
    },
  },
  {
    id: 'dns_dhcp_failure',
    label: '5. DNS / DHCP Service Failure',
    tag: 'Services',
    tone: 'cyan',
    description: 'Severe DNS resolution timeout (4800ms) and DHCP failed while IP connectivity remains reachable.',
    data: {
      performanceSamples: [
        {
          device_id: 'SRV-D5',
          interface_id: 'eth0',
          latency_ms: 14,
          jitter_ms: 2,
          packet_loss_pct: 0,
          throughput_mbps: 500,
          link_utilization_pct: 15,
        },
      ],
      infrastructureSamples: [
        {
          device_id: 'SRV-D5',
          interface_id: 'eth0',
          cpu_utilization_pct: 30,
          memory_utilization_pct: 42,
          interface_errors: 0,
          egress_queue_drops: 0,
          device_status: 'online',
        },
      ],
      devices: [
        { device_id: 'SRV-D5', segment_id: 'services-lan', reachability: 'reachable' },
        { device_id: 'GW-D5', segment_id: 'services-lan', reachability: 'reachable' },
      ],
      links: [
        { link_id: 'L-D5', source_device_id: 'SRV-D5', target_device_id: 'GW-D5', status: 'up' },
      ],
    },
  },
  {
    id: 'interoperability_failure',
    label: '6. Interoperability & Schema Failure',
    tag: 'Interop',
    tone: 'amber',
    description: 'Interoperability status is incompatible between collaborating elements (e.g. schema or unit mismatch).',
    data: {
      performanceSamples: [
        {
          device_id: 'GW-INT6',
          interface_id: 'ge-0/0/0',
          latency_ms: 24,
          jitter_ms: 3,
          packet_loss_pct: 3.8,
          throughput_mbps: 300,
          link_utilization_pct: 25,
        },
      ],
      infrastructureSamples: [
        {
          device_id: 'GW-INT6',
          interface_id: 'ge-0/0/0',
          cpu_utilization_pct: 25,
          memory_utilization_pct: 35,
          interface_errors: 0,
          egress_queue_drops: 0,
          device_status: 'degraded',
        },
      ],
      devices: [
        { device_id: 'GW-INT6', segment_id: 'dmz', reachability: 'reachable' },
        { device_id: 'RTR-EXT', segment_id: 'dmz', reachability: 'reachable' },
      ],
      links: [
        { link_id: 'L-INT6', source_device_id: 'GW-INT6', target_device_id: 'RTR-EXT', status: 'up' },
      ],
    },
  },
]
