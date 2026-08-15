import type { Adapter, Device } from "@/lib/api";

export type BluetoothEvent =
  | { type: "adapter_changed"; timestamp: string; adapter: Adapter }
  | { type: "discovery_started"; timestamp: string; adapter_id: string }
  | { type: "discovery_stopped"; timestamp: string; adapter_id: string }
  | { type: "device_changed"; timestamp: string; device: Device }
  | { type: "device_paired"; timestamp: string; device_id: string }
  | { type: "device_connected"; timestamp: string; device_id: string }
  | { type: "device_disconnected"; timestamp: string; device_id: string }
  | { type: "device_removed"; timestamp: string; device_id: string }
  | {
      type: "pairing_request";
      timestamp: string;
      request: { id: string; kind: string; device_id: string };
    }
  | { type: "pairing_request_resolved"; timestamp: string; request_id: string }
  | {
      type: "characteristic_changed";
      timestamp: string;
      characteristic: { id: string };
    }
  | { type: "ping" };
