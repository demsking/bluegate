<script setup lang="ts">
import { Activity, Bluetooth, Moon, Radio, Sun, Wifi } from "@lucide/vue";
import { computed, onMounted, ref, watch } from "vue";
import { useBluetoothEvents } from "@/composables/useBluetoothEvents";
import {
  createApiClient,
  type Adapter,
  type Device,
  type HealthStatus,
} from "@/lib/api";
import {
  getDefaultNodeId,
  getNodes,
  resolveNode,
  type BlueGateNode,
} from "@/lib/runtime-config";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { BluetoothEvent } from "@/types/events";

type DeviceFilter = "all" | "connected" | "paired" | "unpaired";
type UiTheme = "light" | "dark";

const nodes = ref<BlueGateNode[]>(getNodes());
const selectedNodeId = ref<string>(getDefaultNodeId(nodes.value));
const selectedNode = computed(() =>
  resolveNode(nodes.value, selectedNodeId.value),
);

const health = ref<HealthStatus | null>(null);
const adapters = ref<Adapter[]>([]);
const devices = ref<Device[]>([]);
const error = ref<string | null>(null);
const status = ref<string | null>(null);
const eventFeed = ref<string[]>([]);
const runningOperations = ref<Record<string, boolean>>({});

const query = ref("");
const deviceFilter = ref<DeviceFilter>("all");
const dialogOpen = ref(false);
const selectedDevice = ref<Device | null>(null);

const theme = ref<UiTheme>(
  (localStorage.getItem("bluegate-ui-theme") as UiTheme) ?? "light",
);

const totalConnected = computed(
  () => devices.value.filter((device) => device.connected).length,
);
const totalPaired = computed(
  () => devices.value.filter((device) => device.paired).length,
);

const filteredDevices = computed(() => {
  const normalized = query.value.trim().toLowerCase();

  return devices.value.filter((device) => {
    const target = [device.id, device.alias, device.name, device.address]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesQuery = normalized.length === 0 || target.includes(normalized);

    if (!matchesQuery) {
      return false;
    }

    if (deviceFilter.value === "connected") {
      return device.connected;
    }

    if (deviceFilter.value === "paired") {
      return device.paired;
    }

    if (deviceFilter.value === "unpaired") {
      return !device.paired;
    }

    return true;
  });
});

const client = computed(() => createApiClient(selectedNode.value.apiBaseUrl));

const { connect, disconnect, connected, reconnecting, lastMessageAt } =
  useBluetoothEvents((event) => {
    applyEvent(event);
  });

function applyTheme(nextTheme: UiTheme) {
  const html = document.documentElement;
  html.classList.toggle("dark", nextTheme === "dark");
  localStorage.setItem("bluegate-ui-theme", nextTheme);
}

function toggleTheme() {
  theme.value = theme.value === "dark" ? "light" : "dark";
  applyTheme(theme.value);
}

function pushFeed(line: string) {
  eventFeed.value = [
    `[${selectedNode.value.name}] ${line}`,
    ...eventFeed.value,
  ].slice(0, 30);
}

function operationKey(
  scope: "adapter" | "device",
  id: string,
  action: string,
): string {
  return `${scope}:${id}:${action}`;
}

function isRunning(
  scope: "adapter" | "device",
  id: string,
  action: string,
): boolean {
  return Boolean(runningOperations.value[operationKey(scope, id, action)]);
}

async function runOperation(
  scope: "adapter" | "device",
  id: string,
  action: string,
  operation: () => Promise<void>,
): Promise<void> {
  const key = operationKey(scope, id, action);
  runningOperations.value[key] = true;

  try {
    error.value = null;
    await operation();
  } catch (operationError) {
    error.value =
      operationError instanceof Error
        ? operationError.message
        : "Operation failed.";
  } finally {
    runningOperations.value[key] = false;
  }
}

function upsertAdapter(next: Adapter) {
  const index = adapters.value.findIndex((adapter) => adapter.id === next.id);
  if (index === -1) {
    adapters.value = [next, ...adapters.value];
    return;
  }
  adapters.value[index] = next;
}

function upsertDevice(next: Device) {
  const index = devices.value.findIndex((device) => device.id === next.id);
  if (index === -1) {
    devices.value = [next, ...devices.value];
    return;
  }
  devices.value[index] = next;
  if (selectedDevice.value?.id === next.id) {
    selectedDevice.value = next;
  }
}

function applyEvent(event: BluetoothEvent) {
  if (event.type === "adapter_changed") {
    upsertAdapter(event.adapter);
    pushFeed(`Adapter changed: ${event.adapter.id}`);
    return;
  }

  if (
    event.type === "discovery_started" ||
    event.type === "discovery_stopped"
  ) {
    const status = event.type === "discovery_started";
    adapters.value = adapters.value.map((adapter) =>
      adapter.id === event.adapter_id
        ? { ...adapter, discovering: status }
        : adapter,
    );
    pushFeed(
      `${event.adapter_id}: ${status ? "discovery started" : "discovery stopped"}`,
    );
    return;
  }

  if (event.type === "device_changed") {
    upsertDevice(event.device);
    pushFeed(`Device changed: ${event.device.id}`);
    return;
  }

  if (event.type === "device_removed") {
    devices.value = devices.value.filter(
      (device) => device.id !== event.device_id,
    );
    pushFeed(`Device removed: ${event.device_id}`);
    return;
  }

  if (
    event.type === "device_connected" ||
    event.type === "device_disconnected" ||
    event.type === "device_paired"
  ) {
    pushFeed(
      `Device signal: ${event.type.replace("device_", "")} (${event.device_id})`,
    );
    return;
  }

  if (event.type === "pairing_request") {
    pushFeed(
      `Pairing request: ${event.request.device_id} (${event.request.kind})`,
    );
    return;
  }

  if (event.type === "pairing_request_resolved") {
    pushFeed(`Pairing resolved: ${event.request_id}`);
    return;
  }

  if (event.type === "characteristic_changed") {
    pushFeed(`Characteristic changed: ${event.characteristic.id}`);
  }
}

async function loadDashboard() {
  try {
    error.value = null;
    const [healthResponse, adaptersResponse, devicesResponse] =
      await Promise.all([
        client.value.getHealth(),
        client.value.getAdapters(),
        client.value.getDevices(),
      ]);

    health.value = healthResponse;
    adapters.value = adaptersResponse;
    devices.value = devicesResponse;
  } catch (loadError) {
    error.value =
      loadError instanceof Error
        ? loadError.message
        : "Failed to load BlueGate data.";
  }
}

async function runAdapterToggle(
  adapter: Adapter,
  field: "powered" | "discoverable" | "pairable",
): Promise<void> {
  await runOperation("adapter", adapter.id, field, async () => {
    const updated = await client.value.updateAdapter(adapter.id, {
      [field]: !adapter[field],
    });
    upsertAdapter(updated);
    status.value = `${adapter.id}: ${field} set to ${updated[field] ? "on" : "off"}.`;
    pushFeed(`${adapter.id}: ${field} => ${updated[field] ? "on" : "off"}`);
  });
}

async function runAdapterDiscovery(adapter: Adapter): Promise<void> {
  const action = adapter.discovering ? "stop-scan" : "start-scan";
  await runOperation("adapter", adapter.id, action, async () => {
    if (adapter.discovering) {
      await client.value.stopScan(adapter.id);
      status.value = `${adapter.id}: scan stopped.`;
      pushFeed(`${adapter.id}: scan stopped`);
    } else {
      await client.value.startScan(adapter.id);
      status.value = `${adapter.id}: scan started.`;
      pushFeed(`${adapter.id}: scan started`);
    }

    await loadDashboard();
  });
}

function getCurrentSelectedDevice(): Device | null {
  if (selectedDevice.value == null) {
    return null;
  }

  return (
    devices.value.find((device) => device.id === selectedDevice.value?.id) ??
    null
  );
}

async function runDeviceAction(
  action: "pair" | "connect" | "disconnect" | "trust" | "untrust" | "remove",
): Promise<void> {
  const device = getCurrentSelectedDevice();
  if (device == null) {
    return;
  }

  await runOperation("device", device.id, action, async () => {
    if (action === "pair") {
      await client.value.pairDevice(device.id);
      status.value = `${device.id}: pairing requested.`;
    } else if (action === "connect") {
      await client.value.connectDevice(device.id);
      status.value = `${device.id}: connection requested.`;
    } else if (action === "disconnect") {
      await client.value.disconnectDevice(device.id);
      status.value = `${device.id}: disconnect requested.`;
    } else if (action === "trust") {
      await client.value.trustDevice(device.id);
      status.value = `${device.id}: trust enabled.`;
    } else if (action === "untrust") {
      await client.value.untrustDevice(device.id);
      status.value = `${device.id}: trust removed.`;
    } else {
      await client.value.removeDevice(device.id);
      status.value = `${device.id}: removed.`;
      dialogOpen.value = false;
    }

    pushFeed(`${device.id}: ${action}`);
    await loadDashboard();

    if (action !== "remove") {
      selectedDevice.value =
        devices.value.find((item) => item.id === device.id) ?? null;
    }
  });
}

function openDevice(device: Device) {
  selectedDevice.value = device;
  dialogOpen.value = true;
}

watch(selectedNodeId, async () => {
  disconnect();
  eventFeed.value = [];
  await loadDashboard();
  connect(selectedNode.value.apiBaseUrl);
});

onMounted(async () => {
  applyTheme(theme.value);
  await loadDashboard();
  connect(selectedNode.value.apiBaseUrl);
});
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <main
      class="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8"
    >
      <Card>
        <CardHeader
          class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <div>
            <CardDescription class="font-medium uppercase tracking-[0.2em]">
              BlueGate UI
            </CardDescription>
            <CardTitle class="mt-1 text-3xl font-semibold"
              >Multi-node Bluetooth dashboard</CardTitle
            >
          </div>
          <div class="grid w-full gap-2 sm:flex sm:w-auto sm:items-center">
            <Select v-model="selectedNodeId">
              <SelectTrigger class="w-full sm:w-[260px]">
                <SelectValue placeholder="Select node" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="node in nodes"
                  :key="node.id"
                  :value="node.id"
                >
                  {{ node.name }}
                </SelectItem>
              </SelectContent>
            </Select>
            <Badge :variant="connected ? 'default' : 'secondary'">{{
              connected ? "Live" : reconnecting ? "Reconnecting" : "Offline"
            }}</Badge>
            <Button variant="outline" size="icon" @click="toggleTheme">
              <Sun v-if="theme === 'dark'" class="h-4 w-4" />
              <Moon v-else class="h-4 w-4" />
            </Button>
            <Button variant="outline" @click="loadDashboard">Refresh</Button>
          </div>
        </CardHeader>
      </Card>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader class="pb-2">
            <CardDescription class="flex items-center gap-2"
              ><Bluetooth class="h-4 w-4" /> BlueZ</CardDescription
            >
            <CardTitle class="text-2xl">{{
              health?.bluez ?? "unknown"
            }}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader class="pb-2">
            <CardDescription class="flex items-center gap-2"
              ><Wifi class="h-4 w-4" /> D-Bus</CardDescription
            >
            <CardTitle class="text-2xl">{{
              health?.dbus ?? "unknown"
            }}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader class="pb-2">
            <CardDescription class="flex items-center gap-2"
              ><Radio class="h-4 w-4" /> Connected devices</CardDescription
            >
            <CardTitle class="text-2xl">{{ totalConnected }}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader class="pb-2">
            <CardDescription class="flex items-center gap-2"
              ><Activity class="h-4 w-4" /> Paired devices</CardDescription
            >
            <CardTitle class="text-2xl">{{ totalPaired }}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div
        v-if="error"
        class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
      >
        {{ error }}
      </div>
      <div
        v-if="status"
        class="rounded-md border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground"
      >
        {{ status }}
      </div>

      <div class="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle class="text-xl">Devices</CardTitle>
            <CardDescription
              >Filter and inspect all discovered Bluetooth
              endpoints.</CardDescription
            >
          </CardHeader>
          <CardContent class="space-y-4">
            <Input
              v-model="query"
              placeholder="Search by id, name, alias, or MAC"
            />

            <Tabs v-model="deviceFilter" class="w-full">
              <TabsList class="grid w-full grid-cols-4">
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="connected">Connected</TabsTrigger>
                <TabsTrigger value="paired">Paired</TabsTrigger>
                <TabsTrigger value="unpaired">Unpaired</TabsTrigger>
              </TabsList>
              <TabsContent value="all" class="mt-4" />
              <TabsContent value="connected" class="mt-4" />
              <TabsContent value="paired" class="mt-4" />
              <TabsContent value="unpaired" class="mt-4" />
            </Tabs>

            <ScrollArea class="h-[24rem] rounded-md border border-border/70">
              <div class="space-y-2 p-2">
                <Button
                  v-for="device in filteredDevices"
                  :key="device.id"
                  variant="ghost"
                  class="h-auto w-full justify-between border border-transparent px-3 py-3 hover:border-border hover:bg-muted/50"
                  @click="openDevice(device)"
                >
                  <div class="text-left">
                    <p class="font-medium leading-none">
                      {{ device.alias || device.name || device.id }}
                    </p>
                    <p class="mt-1 text-xs text-muted-foreground">
                      {{ device.address || device.id }}
                    </p>
                  </div>
                  <div class="flex items-center gap-2">
                    <Badge
                      :variant="device.connected ? 'default' : 'secondary'"
                      >{{ device.connected ? "Connected" : "Idle" }}</Badge
                    >
                    <Badge :variant="device.paired ? 'default' : 'outline'">{{
                      device.paired ? "Paired" : "Unpaired"
                    }}</Badge>
                  </div>
                </Button>
                <p
                  v-if="filteredDevices.length === 0"
                  class="px-3 py-6 text-sm text-muted-foreground"
                >
                  No devices match this filter.
                </p>
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle class="text-xl">Live activity</CardTitle>
            <CardDescription>
              Node: {{ selectedNode.name }}
              <span class="mx-1">|</span>
              Last message:
              {{
                lastMessageAt
                  ? new Date(lastMessageAt).toLocaleTimeString()
                  : "waiting for events"
              }}
            </CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="space-y-2">
              <p class="text-sm font-medium">Adapters</p>
              <div class="space-y-2">
                <div
                  v-for="adapter in adapters"
                  :key="adapter.id"
                  class="space-y-2 rounded-md border border-border/70 px-3 py-2 text-sm"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span>{{
                      adapter.alias || adapter.name || adapter.id
                    }}</span>
                    <div class="flex items-center gap-2">
                      <Badge
                        :variant="adapter.powered ? 'default' : 'secondary'"
                        >{{ adapter.powered ? "On" : "Off" }}</Badge
                      >
                      <Badge
                        :variant="adapter.discovering ? 'default' : 'outline'"
                        >{{ adapter.discovering ? "Scanning" : "Idle" }}</Badge
                      >
                    </div>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      :disabled="isRunning('adapter', adapter.id, 'powered')"
                      @click="runAdapterToggle(adapter, 'powered')"
                    >
                      {{ adapter.powered ? "Power Off" : "Power On" }}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      :disabled="
                        isRunning('adapter', adapter.id, 'discoverable')
                      "
                      @click="runAdapterToggle(adapter, 'discoverable')"
                    >
                      {{
                        adapter.discoverable ? "Undiscoverable" : "Discoverable"
                      }}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      :disabled="isRunning('adapter', adapter.id, 'pairable')"
                      @click="runAdapterToggle(adapter, 'pairable')"
                    >
                      {{ adapter.pairable ? "Unpairable" : "Pairable" }}
                    </Button>
                    <Button
                      size="sm"
                      :disabled="
                        isRunning(
                          'adapter',
                          adapter.id,
                          adapter.discovering ? 'stop-scan' : 'start-scan',
                        )
                      "
                      @click="runAdapterDiscovery(adapter)"
                    >
                      {{ adapter.discovering ? "Stop Scan" : "Start Scan" }}
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            <ScrollArea class="h-[13rem] rounded-md border border-border/70">
              <ul class="space-y-1 p-2 text-xs text-muted-foreground">
                <li
                  v-for="(entry, index) in eventFeed"
                  :key="`${entry}-${index}`"
                  class="rounded px-2 py-1 hover:bg-muted/60"
                >
                  {{ entry }}
                </li>
                <li v-if="eventFeed.length === 0" class="px-2 py-1">
                  No activity yet.
                </li>
              </ul>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </main>

    <Dialog v-model:open="dialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{
            selectedDevice?.alias || selectedDevice?.name || selectedDevice?.id
          }}</DialogTitle>
          <DialogDescription>{{
            selectedDevice?.address || selectedDevice?.id
          }}</DialogDescription>
        </DialogHeader>

        <div v-if="selectedDevice" class="grid gap-3 sm:grid-cols-2">
          <Card>
            <CardHeader class="p-4 pb-2">
              <CardDescription>Connection</CardDescription>
              <CardTitle class="text-base">{{
                selectedDevice.connected ? "Connected" : "Disconnected"
              }}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader class="p-4 pb-2">
              <CardDescription>Pairing</CardDescription>
              <CardTitle class="text-base">{{
                selectedDevice.paired ? "Paired" : "Unpaired"
              }}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader class="p-4 pb-2">
              <CardDescription>Trust</CardDescription>
              <CardTitle class="text-base">{{
                selectedDevice.trusted ? "Trusted" : "Not trusted"
              }}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader class="p-4 pb-2">
              <CardDescription>RSSI</CardDescription>
              <CardTitle class="text-base">{{
                selectedDevice.rssi ?? "n/a"
              }}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        <div v-if="selectedDevice" class="mt-4 flex flex-wrap gap-2">
          <Button
            size="sm"
            :disabled="
              selectedDevice.paired ||
              isRunning('device', selectedDevice.id, 'pair')
            "
            @click="runDeviceAction('pair')"
          >
            Pair
          </Button>
          <Button
            size="sm"
            variant="outline"
            :disabled="
              selectedDevice.connected ||
              isRunning('device', selectedDevice.id, 'connect')
            "
            @click="runDeviceAction('connect')"
          >
            Connect
          </Button>
          <Button
            size="sm"
            variant="outline"
            :disabled="
              !selectedDevice.connected ||
              isRunning('device', selectedDevice.id, 'disconnect')
            "
            @click="runDeviceAction('disconnect')"
          >
            Disconnect
          </Button>
          <Button
            size="sm"
            variant="outline"
            :disabled="
              selectedDevice.trusted ||
              isRunning('device', selectedDevice.id, 'trust')
            "
            @click="runDeviceAction('trust')"
          >
            Trust
          </Button>
          <Button
            size="sm"
            variant="outline"
            :disabled="
              !selectedDevice.trusted ||
              isRunning('device', selectedDevice.id, 'untrust')
            "
            @click="runDeviceAction('untrust')"
          >
            Untrust
          </Button>
          <Button
            size="sm"
            variant="destructive"
            :disabled="isRunning('device', selectedDevice.id, 'remove')"
            @click="runDeviceAction('remove')"
          >
            Remove
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>
