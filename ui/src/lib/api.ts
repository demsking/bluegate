export type HealthStatus = {
  status: "healthy" | "degraded";
  application: "ready";
  dbus: "connected" | "disconnected";
  bluez: "available" | "unavailable";
  adapters: number;
  version: string;
};

export type Adapter = {
  id: string;
  object_path: string;
  name: string | null;
  alias: string | null;
  address: string | null;
  powered: boolean;
  discoverable: boolean;
  pairable: boolean;
  discovering: boolean;
  device_count: number;
};

export type Device = {
  id: string;
  object_path: string;
  adapter_id: string;
  name: string | null;
  alias: string | null;
  address: string | null;
  address_type: string | null;
  icon: string | null;
  device_class: number | null;
  appearance: number | null;
  rssi: number | null;
  tx_power: number | null;
  paired: boolean;
  trusted: boolean;
  connected: boolean;
  blocked: boolean;
  services_resolved: boolean;
  uuids: string[];
};

type AdapterPatch = {
  powered?: boolean;
  discoverable?: boolean;
  pairable?: boolean;
};

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
}

async function request<T>(
  baseUrl: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(
      `Request failed (${response.status}): ${response.statusText}`,
    );
  }

  return (await response.json()) as T;
}

export function createApiClient(baseUrl: string) {
  return {
    getHealth: () => request<HealthStatus>(baseUrl, "/health/"),
    getAdapters: () => request<Adapter[]>(baseUrl, "/adapters/"),
    getDevices: () => request<Device[]>(baseUrl, "/devices/"),
    updateAdapter: (adapterId: string, patch: AdapterPatch) =>
      request<Adapter>(baseUrl, `/adapters/${encodeURIComponent(adapterId)}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    startScan: (adapterId: string) =>
      request<{ started: boolean }>(
        baseUrl,
        `/adapters/${encodeURIComponent(adapterId)}/scan`,
        {
          method: "POST",
        },
      ),
    stopScan: (adapterId: string) =>
      request<{ stopped: boolean }>(
        baseUrl,
        `/adapters/${encodeURIComponent(adapterId)}/scan`,
        {
          method: "DELETE",
        },
      ),
    pairDevice: (deviceId: string) =>
      request<{ paired: boolean }>(
        baseUrl,
        `/devices/${encodeURIComponent(deviceId)}/pair`,
        {
          method: "POST",
        },
      ),
    connectDevice: (deviceId: string) =>
      request<{ connected: boolean }>(
        baseUrl,
        `/devices/${encodeURIComponent(deviceId)}/connect`,
        {
          method: "POST",
        },
      ),
    disconnectDevice: (deviceId: string) =>
      request<{ disconnected: boolean }>(
        baseUrl,
        `/devices/${encodeURIComponent(deviceId)}/disconnect`,
        {
          method: "POST",
        },
      ),
    trustDevice: (deviceId: string) =>
      request<{ trusted: boolean }>(
        baseUrl,
        `/devices/${encodeURIComponent(deviceId)}/trust`,
        {
          method: "POST",
        },
      ),
    untrustDevice: (deviceId: string) =>
      request<{ trusted: boolean }>(
        baseUrl,
        `/devices/${encodeURIComponent(deviceId)}/untrust`,
        {
          method: "POST",
        },
      ),
    removeDevice: (deviceId: string) =>
      request<{ removed: boolean }>(
        baseUrl,
        `/devices/${encodeURIComponent(deviceId)}`,
        {
          method: "DELETE",
        },
      ),
  };
}
