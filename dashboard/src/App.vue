<script setup lang="ts">
import {
  Bluetooth,
  ChevronRight,
  CircleHelp,
  Gamepad2,
  Headphones,
  Laptop,
  Pencil,
  Phone,
  RefreshCw,
  Server,
  Settings2,
  Speaker,
  Watch,
} from "@lucide/vue";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { useLocalStorage } from "@vueuse/core";
import {
  createApiClient,
  type Adapter,
  type Device,
  type HealthStatus,
} from "@/lib/api";
import {
  getDefaultNodeId,
  getNodeProxyBaseUrl,
  loadNodes,
  resolveNode,
  type BlueGateNode,
} from "@/lib/runtime-config";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";

import {
  Item,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";

import { TooltipProvider } from "@/components/ui/tooltip";

import "vue-sonner/style.css";

import { toast } from "vue-sonner";
import { Toaster } from "@/components/ui/sonner";

type NodeSnapshot = {
  node: BlueGateNode;
  health: HealthStatus | null;
  adapters: Adapter[];
  error: string | null;
};

const nodes = ref<BlueGateNode[]>([]);
const nodesLoaded = ref(false);
const showGlobalEmptyState = computed(
  () => nodesLoaded.value && nodes.value.length === 0,
);
const selectedNodeId = useLocalStorage<string>("bluegate:selected-node-id", "");
const selectedNode = computed(
  () => resolveNode(nodes.value, selectedNodeId.value) ?? null,
);

const nodeSnapshots = ref<NodeSnapshot[]>([]);
const dashboardLoading = ref(false);
const devices = ref<Device[]>([]);
const error = ref<string | null>(null);
const runningOperations = ref<Record<string, boolean>>({});

const selectedAdapterByNode = useLocalStorage<Record<string, string>>(
  "bluegate:selected-adapter-by-node",
  {},
);
const selectedAdapterId = computed<string>({
  get() {
    const nodeId = selectedNodeId.value;

    if (nodeId.length === 0) {
      return "";
    }

    return selectedAdapterByNode.value[nodeId] ?? "";
  },
  set(adapterId: string) {
    const nodeId = selectedNodeId.value;

    if (nodeId.length === 0) {
      return;
    }

    if (adapterId.length === 0) {
      if (!(nodeId in selectedAdapterByNode.value)) {
        return;
      }

      const nextByNode = { ...selectedAdapterByNode.value };
      delete nextByNode[nodeId];
      selectedAdapterByNode.value = nextByNode;
      return;
    }

    if (selectedAdapterByNode.value[nodeId] === adapterId) {
      return;
    }

    selectedAdapterByNode.value = {
      ...selectedAdapterByNode.value,
      [nodeId]: adapterId,
    };
  },
});
const selectedDevice = ref<Device | null>(null);
const deviceSheetOpen = ref(false);
const disconnectConfirmOpen = ref(false);
const unpairConfirmOpen = ref(false);
const selectorOpen = ref(false);
const adapterSettingsOpen = ref(false);
const deviceNameDrawerOpen = ref(false);
const selectedDeviceNameDrawerOpen = ref(false);
const serverDeviceName = ref("");
const selectedDeviceName = ref("");
const availableSectionRef = ref<HTMLElement | null>(null);
const autoScanArmed = ref(true);
const pullRefreshStartY = ref<number | null>(null);
const pullRefreshDistance = ref(0);

const pullRefreshProgress = computed(() =>
  Math.min(pullRefreshDistance.value / 90, 1),
);

const pullRefreshIndicatorStyle = computed(() => ({
  transform: `translateY(${Math.min(pullRefreshDistance.value * 0.5, 36)}px) rotate(${pullRefreshDistance.value * 1.5}deg) scale(${1 + pullRefreshProgress.value * 0.08})`,
  opacity: String(Math.min(0.35 + pullRefreshProgress.value, 1)),
}));

let availableObserver: IntersectionObserver | null = null;

const client = computed(() => {
  if (selectedNode.value == null) {
    return null;
  }

  return createApiClient(getNodeProxyBaseUrl(selectedNode.value.id));
});

const selectedNodeSnapshot = computed(
  () =>
    nodeSnapshots.value.find(
      (snapshot) => snapshot.node.id === selectedNodeId.value,
    ) ?? null,
);
const selectedNodeAdapters = computed(
  () => selectedNodeSnapshot.value?.adapters ?? [],
);
const selectedAdapter = computed(
  () =>
    selectedNodeAdapters.value.find(
      (adapter) => adapter.id === selectedAdapterId.value,
    ) ?? null,
);

const filteredDevices = computed(() => {
  const adapterId = selectedAdapterId.value;

  if (adapterId.length === 0) {
    return [];
  }

  return devices.value.filter((device) => device.adapter_id === adapterId);
});

const connectedDevices = computed(() =>
  filteredDevices.value.filter((device) => device.connected),
);
const savedDevices = computed(() =>
  filteredDevices.value.filter((device) => device.paired && !device.connected),
);
const availableDevices = computed(() =>
  filteredDevices.value.filter((device) => !device.paired),
);

function nodeSnapshotFor(nodeId: string): NodeSnapshot | null {
  return (
    nodeSnapshots.value.find((snapshot) => snapshot.node.id === nodeId) ?? null
  );
}

function syncSelectedNode(): void {
  if (nodes.value.length === 0) {
    selectedNodeId.value = "";
    return;
  }

  const exists = nodes.value.some((node) => node.id === selectedNodeId.value);

  if (!exists) {
    selectedNodeId.value = getDefaultNodeId(nodes.value) ?? nodes.value[0].id;
  }
}

function nodeTitle(node: BlueGateNode): string {
  return node.name || node.id;
}

function adapterTitle(adapter: Adapter): string {
  return adapter.alias || adapter.name || adapter.id;
}

function nodeAdapters(nodeId: string): Adapter[] {
  return nodeSnapshotFor(nodeId)?.adapters ?? [];
}

function nodeSingleAdapter(nodeId: string): Adapter | null {
  const adapters = nodeAdapters(nodeId);
  return adapters.length === 1 ? adapters[0] : null;
}

function nodeHasMultipleAdapters(nodeId: string): boolean {
  return nodeAdapters(nodeId).length > 1;
}

function selectedNodeSummary(): string {
  if (selectedNode.value == null) {
    return "No node available";
  }

  return nodeTitle(selectedNode.value);
}

function selectedAdapterSummary(): string {
  if (selectedAdapter.value == null) {
    return "Select an adapter";
  }

  return `${selectedAdapter.value.id} — ${adapterTitle(selectedAdapter.value)}`;
}

function selectedNodeBadge(): string {
  if (selectedNodeSnapshot.value?.health == null) {
    return "Unknown";
  }

  return `${selectedNodeSnapshot.value.health.dbus} · ${selectedNodeSnapshot.value.health.bluez}`;
}

const appVersion = computed(
  () => selectedNodeSnapshot.value?.health?.version ?? "dev",
);

function syncServerDeviceName(): void {
  if (selectedAdapter.value == null) {
    serverDeviceName.value = "";
    return;
  }

  serverDeviceName.value =
    selectedAdapter.value.alias ||
    selectedAdapter.value.name ||
    selectedAdapter.value.id;
}

function syncSelectedDeviceName(): void {
  if (selectedDevice.value == null) {
    selectedDeviceName.value = "";
    return;
  }

  selectedDeviceName.value =
    selectedDevice.value.alias ||
    selectedDevice.value.name ||
    selectedDevice.value.id;
}

function syncSelectedAdapter(): void {
  if (selectedNodeAdapters.value.length === 0) {
    return;
  }

  const exists = selectedNodeAdapters.value.some(
    (adapter) => adapter.id === selectedAdapterId.value,
  );

  if (!exists) {
    selectedAdapterId.value = selectedNodeAdapters.value[0].id;
  }
}

function deviceTitle(device: Device): string {
  return device.alias || device.name || device.id;
}

function deviceSubtitle(device: Device): string {
  return device.address || device.id;
}

function getDeviceIconComponent(device: Device) {
  const value =
    `${device.icon ?? ""} ${device.name ?? ""} ${device.alias ?? ""}`.toLowerCase();

  if (/(earbud|earphone|in-ear|buds)/.test(value)) {
    return Headphones;
  }

  if (/(headset|headphone|audio-headset)/.test(value)) {
    return Headphones;
  }

  if (/(phone|smartphone|cellphone|mobile)/.test(value)) {
    return Phone;
  }

  if (/(speaker|audio-card|speakerphone)/.test(value)) {
    return Speaker;
  }

  if (/(watch|smartwatch|wearable)/.test(value)) {
    return Watch;
  }

  if (/(laptop|computer|desktop|pc|tablet)/.test(value)) {
    return Laptop;
  }

  if (/(gamepad|controller|joystick)/.test(value)) {
    return Gamepad2;
  }

  return Bluetooth;
}

function openDevice(device: Device): void {
  selectedDevice.value = device;
  deviceSheetOpen.value = true;
  syncSelectedDeviceName();
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

function extractErrorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : "Request failed.";
}

async function loadNodeSnapshots(): Promise<void> {
  const snapshots: NodeSnapshot[] = await Promise.all(
    nodes.value.map(async (node) => {
      const api = createApiClient(getNodeProxyBaseUrl(node.id));

      try {
        const [health, adapters] = await Promise.all([
          api.getHealth(),
          api.getAdapters(),
        ]);
        return { node, health, adapters, error: null };
      } catch (snapshotError) {
        return {
          node,
          health: null,
          adapters: [],
          error: extractErrorMessage(snapshotError),
        };
      }
    }),
  );

  nodeSnapshots.value = snapshots;
}

async function loadDashboard(): Promise<void> {
  syncSelectedNode();

  const api = client.value;

  if (selectedNode.value == null || api == null) {
    devices.value = [];
    nodeSnapshots.value = [];
    selectedAdapterId.value = "";
    return;
  }

  try {
    dashboardLoading.value = true;
    error.value = null;

    await loadNodeSnapshots();

    const devicesResponse = await api.getDevices();
    devices.value = devicesResponse;
    syncSelectedAdapter();
    syncServerDeviceName();
  } catch (loadError) {
    error.value =
      loadError instanceof Error
        ? loadError.message
        : "Failed to load BlueGate data.";
  } finally {
    dashboardLoading.value = false;
  }
}

async function runAdapterToggle(
  adapter: Adapter,
  field: "powered" | "discoverable" | "pairable",
): Promise<void> {
  const api = client.value;

  if (api == null) {
    return;
  }

  await runOperation("adapter", adapter.id, field, async () => {
    await api.updateAdapter(adapter.id, {
      [field]: !adapter[field],
    });

    await loadDashboard();
  });
}

async function saveAdapterName(): Promise<void> {
  const adapter = selectedAdapter.value;
  const api = client.value;

  if (adapter == null || api == null) {
    return;
  }

  const nextAlias = serverDeviceName.value.trim();

  await runOperation("adapter", adapter.id, "alias", async () => {
    const updated = await api.updateAdapter(adapter.id, {
      alias: nextAlias.length > 0 ? nextAlias : null,
    });

    serverDeviceName.value = updated.alias || updated.name || updated.id;
    await loadDashboard();
    deviceNameDrawerOpen.value = false;
  });
}

async function startAdapterScan(
  adapter: Adapter,
  source: "auto" | "manual" = "manual",
): Promise<void> {
  const api = client.value;
  if (api == null || adapter.discovering) {
    return;
  }

  await runOperation("adapter", adapter.id, "start-scan", async () => {
    await api.startScan(adapter.id);

    if (source === "auto") {
      autoScanArmed.value = false;
    }

    await loadDashboard();
  });
}

async function stopAdapterScan(adapter: Adapter): Promise<void> {
  const api = client.value;
  if (api == null || !adapter.discovering) {
    return;
  }

  await runOperation("adapter", adapter.id, "stop-scan", async () => {
    await api.stopScan(adapter.id);
    await loadDashboard();
  });
}

async function stopAdapterScanForNode(
  nodeId: string,
  adapterId: string,
): Promise<void> {
  const snapshot = nodeSnapshotFor(nodeId);
  const adapter = snapshot?.adapters.find(
    (candidate) => candidate.id === adapterId,
  );

  if (adapter == null || !adapter.discovering) {
    return;
  }

  await createApiClient(getNodeProxyBaseUrl(nodeId)).stopScan(adapter.id);
}

async function toggleSelectedAdapterScan(): Promise<void> {
  if (selectedAdapter.value == null) {
    return;
  }

  if (selectedAdapter.value.discovering) {
    await stopAdapterScan(selectedAdapter.value);
    return;
  }

  await startAdapterScan(selectedAdapter.value);
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

type DeviceDrawerAction = "pair" | "connect" | "disconnect" | "unpair";

function resolveDeviceDrawerActions(device: Device): DeviceDrawerAction[] {
  if (device.blocked) {
    return ["unpair"];
  }

  if (device.connected) {
    return ["disconnect", "unpair"];
  }

  if (device.paired) {
    return ["connect", "unpair"];
  }

  return ["pair"];
}

function deviceStatus(device: Device): string {
  if (device.blocked) {
    return "Blocked";
  }

  if (device.connected) {
    const statuses = ["Connected"];

    if (device.battery_level != null) {
      statuses.push(`Battery ${device.battery_level}%`);
    }

    return statuses.join(" • ");
  }

  if (device.paired) {
    return "Saved";
  }

  return device.name ? device.address || device.id : "";
}

function deviceActionLabel(action: DeviceDrawerAction): string {
  if (action === "pair") {
    return "Pair";
  }

  if (action === "unpair") {
    return "Unpair";
  }

  if (action === "connect") {
    return "Connect";
  }

  return "Disconnect";
}

function deviceActionClass(action: DeviceDrawerAction): string {
  if (action === "disconnect" || action === "unpair") {
    return "border-rose-500/30 bg-rose-500/10 text-rose-100";
  }

  return "border-sky-500/35 bg-sky-500/15 text-sky-100";
}

function handleDeviceActionClick(action: DeviceDrawerAction): void {
  if (action === "disconnect") {
    deviceSheetOpen.value = false;
    disconnectConfirmOpen.value = true;
    return;
  }

  if (action !== "unpair") {
    void runDeviceAction(action);
    return;
  }

  deviceSheetOpen.value = false;
  unpairConfirmOpen.value = true;
}

function cancelUnpairConfirmation(): void {
  unpairConfirmOpen.value = false;

  if (selectedDevice.value != null) {
    deviceSheetOpen.value = true;
  }
}

function cancelDisconnectConfirmation(): void {
  disconnectConfirmOpen.value = false;

  if (selectedDevice.value != null) {
    deviceSheetOpen.value = true;
  }
}

async function confirmDisconnectDevice(): Promise<void> {
  disconnectConfirmOpen.value = false;
  await runDeviceAction("disconnect");
}

async function confirmUnpairDevice(): Promise<void> {
  unpairConfirmOpen.value = false;
  await runDeviceAction("unpair");
}

async function runDeviceAction(
  action:
    | "pair"
    | "unpair"
    | "connect"
    | "disconnect"
    | "trust"
    | "untrust"
    | "remove",
): Promise<void> {
  const api = client.value;
  if (api == null) {
    return;
  }

  const device = getCurrentSelectedDevice();
  if (device == null) {
    return;
  }

  await runOperation("device", device.id, action, async () => {
    if (action === "pair") {
      await api.pairDevice(device.id);
      await api.trustDevice(device.id);
      await api.connectDevice(device.id);
    } else if (action === "unpair") {
      await api.unpairDevice(device.id);
    } else if (action === "connect") {
      await api.connectDevice(device.id);
    } else if (action === "disconnect") {
      await api.disconnectDevice(device.id);
    } else if (action === "trust") {
      await api.trustDevice(device.id);
    } else if (action === "untrust") {
      await api.untrustDevice(device.id);
    } else {
      await api.removeDevice(device.id);
    }

    await loadDashboard();
    deviceSheetOpen.value = false;
    selectedDevice.value = null;
    selectedDeviceNameDrawerOpen.value = false;
  });
}

function openSelectedDeviceNameDrawer(): void {
  if (selectedDevice.value == null) {
    return;
  }

  syncSelectedDeviceName();
  selectedDeviceNameDrawerOpen.value = true;
}

async function saveSelectedDeviceName(): Promise<void> {
  const api = client.value;
  const device = getCurrentSelectedDevice();

  if (api == null || device == null) {
    return;
  }

  const nextAlias = selectedDeviceName.value.trim();
  if (nextAlias.length === 0) {
    return;
  }

  await runOperation("device", device.id, "alias", async () => {
    const updated = await api.updateDevice(device.id, {
      alias: nextAlias,
    });

    selectedDevice.value = updated;
    selectedDeviceName.value = updated.alias || updated.name || updated.id;
    await loadDashboard();
    selectedDeviceNameDrawerOpen.value = false;
  });
}

function resetPullRefresh(): void {
  pullRefreshStartY.value = null;
  pullRefreshDistance.value = 0;
}

function handleSwipeRefreshStart(event: TouchEvent): void {
  if (dashboardLoading.value || window.scrollY > 0) {
    return;
  }

  if (event.touches.length !== 1) {
    return;
  }

  pullRefreshStartY.value = event.touches[0].clientY;
}

function handleSwipeRefreshMove(event: TouchEvent): void {
  if (pullRefreshStartY.value == null || dashboardLoading.value) {
    return;
  }

  const deltaY = event.touches[0].clientY - pullRefreshStartY.value;
  if (deltaY <= 0) {
    pullRefreshDistance.value = 0;
    return;
  }

  pullRefreshDistance.value = Math.min(deltaY * 0.8, 110);

  if (pullRefreshDistance.value > 0) {
    event.preventDefault();
  }
}

function handleSwipeRefreshEnd(): void {
  if (pullRefreshDistance.value >= 80) {
    void refreshDashboardAndScan();
  }

  resetPullRefresh();
}

async function refreshDashboardAndScan(): Promise<void> {
  autoScanArmed.value = true;
  await loadDashboard();

  if (selectedAdapter.value != null) {
    await startAdapterScan(selectedAdapter.value, "manual");
  }
}

async function selectNodeAdapter(
  nodeId: string,
  adapterId: string,
): Promise<void> {
  const previousNodeId = selectedNodeId.value;
  const previousAdapterId = selectedAdapterId.value;

  if (previousNodeId === nodeId && previousAdapterId === adapterId) {
    selectorOpen.value = false;
    return;
  }

  if (previousNodeId.length > 0 && previousAdapterId.length > 0) {
    try {
      await stopAdapterScanForNode(previousNodeId, previousAdapterId);
    } catch (stopError) {
      error.value = extractErrorMessage(stopError);
    }
  }

  if (selectedNodeId.value !== nodeId) {
    selectedNodeId.value = nodeId;
  }

  selectedAdapterId.value = adapterId;
  selectorOpen.value = false;
  deviceSheetOpen.value = false;
  adapterSettingsOpen.value = false;
  autoScanArmed.value = true;
}

function openSelectedAdapterSettings(): void {
  if (selectedAdapter.value == null) {
    return;
  }

  syncServerDeviceName();
  adapterSettingsOpen.value = true;
}

function openRenameAdapterDrawer(): void {
  if (selectedAdapter.value == null) {
    return;
  }

  syncServerDeviceName();
  deviceNameDrawerOpen.value = true;
}

async function startAdapterScanIfVisible(): Promise<void> {
  if (!autoScanArmed.value || selectedAdapter.value == null) {
    return;
  }

  if (selectedAdapter.value.discovering) {
    autoScanArmed.value = false;
    return;
  }

  await startAdapterScan(selectedAdapter.value, "auto");
}

watch(selectedNodeId, async (nextNodeId) => {
  if (!nodesLoaded.value) {
    return;
  }

  if (nextNodeId.length === 0) {
    selectedDevice.value = null;
    nodeSnapshots.value = [];
    devices.value = [];
    return;
  }

  selectedDevice.value = null;
  autoScanArmed.value = true;
  await loadDashboard();
});

watch(selectedAdapterId, () => {
  selectedDevice.value = null;
  selectedDeviceNameDrawerOpen.value = false;
  selectedDeviceName.value = "";
  autoScanArmed.value = true;
  syncServerDeviceName();
});

watch(
  () => selectedDevice.value?.id,
  (nextId) => {
    if (nextId == null) {
      disconnectConfirmOpen.value = false;
      unpairConfirmOpen.value = false;
      return;
    }

    const updated = devices.value.find((device) => device.id === nextId);
    if (updated != null) {
      selectedDevice.value = updated;
      syncSelectedDeviceName();
    }
  },
);

watch(error, (nextError) => {
  if (!nextError) {
    return;
  }

  toast({
    title: "Request failed",
    description: nextError,
    variant: "error",
    duration: 4200,
  });

  error.value = null;
});

onMounted(async () => {
  document.documentElement.classList.add("dark");

  nodes.value = await loadNodes();
  syncSelectedNode();
  nodesLoaded.value = true;

  await loadDashboard();
  syncServerDeviceName();

  await nextTick();
  availableObserver = new IntersectionObserver(
    (entries) => {
      const entry = entries[0];
      if (!entry?.isIntersecting) {
        return;
      }

      void startAdapterScanIfVisible();
    },
    {
      root: null,
      rootMargin: "0px 0px -35% 0px",
      threshold: 0.25,
    },
  );

  if (availableSectionRef.value != null) {
    availableObserver.observe(availableSectionRef.value);
  }
});

onBeforeUnmount(() => {
  availableObserver?.disconnect();
  availableObserver = null;
});
</script>

<template>
  <div
    class="flex min-h-screen flex-col bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.20),transparent_36%),linear-gradient(180deg,#020617,#09090b_40%,#030712_100%)] px-3 py-5 text-slate-100 sm:px-4 sm:py-6"
  >
    <main
      v-if="showGlobalEmptyState"
      class="mx-auto grid min-h-[calc(100vh-2.5rem)] w-full max-w-117.5 flex-1 place-items-center"
    >
      <section
        class="w-full rounded-[1.8rem] p-6 text-center shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl"
      >
        <div
          class="mx-auto mb-4 grid size-16 place-items-center overflow-hidden"
        >
          <img
            src="/favicon.png"
            alt="BlueGate app icon"
            class="size-full object-cover"
          />
        </div>
        <p class="m-0 text-xs uppercase tracking-[0.28em] text-slate-500">
          BlueGate
        </p>
        <h2 class="mt-3 text-2xl font-semibold tracking-tight text-slate-100">
          No Nodes Configured
        </h2>
        <p class="mt-2 text-sm text-slate-400">
          This app is ready, but no Bluetooth nodes are available yet.
        </p>
        <a
          href="https://demsking.gitlab.io/bluegate/"
          target="_blank"
          rel="noreferrer"
          class="mt-4 inline-flex items-center justify-center rounded-full border border-sky-400/30 bg-sky-500/10 px-3 py-2 text-sm font-medium text-sky-100 transition-colors hover:bg-sky-500/15"
        >
          How to add nodes
        </a>
      </section>
    </main>

    <main
      v-else
      class="mx-auto flex w-full max-w-117.5 flex-1 flex-col gap-3"
      @touchstart="handleSwipeRefreshStart"
      @touchmove="handleSwipeRefreshMove"
      @touchend="handleSwipeRefreshEnd"
      @touchcancel="handleSwipeRefreshEnd"
    >
      <div
        v-if="pullRefreshDistance > 0"
        class="pointer-events-none flex justify-center transition-all duration-150"
      >
        <div
          class="grid size-10 place-items-center rounded-full border border-sky-400/30 bg-sky-500/10 text-sky-100 shadow-[0_12px_30px_rgba(14,165,233,0.25)]"
          :style="pullRefreshIndicatorStyle"
        >
          <RefreshCw
            :size="18"
            :class="
              dashboardLoading || pullRefreshDistance > 18 ? 'animate-spin' : ''
            "
          />
        </div>
      </div>

      <header class="mb-1 flex items-center justify-between">
        <h1 class="m-0 text-2xl font-medium tracking-tight">BlueGate</h1>
        <button
          class="grid size-9 place-items-center rounded-full border border-white/10 bg-white/5 text-slate-200"
          type="button"
          aria-label="Help"
        >
          <CircleHelp :size="22" />
        </button>
      </header>

      <section
        class="rounded-[1.8rem] border border-white/8 bg-white/5 p-3 shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl"
      >
        <button
          type="button"
          class="flex w-full items-center gap-3 rounded-[1.45rem] border border-white/8 bg-slate-950/65 px-4 py-4 text-left transition-transform duration-200 ease-out active:scale-[0.99]"
          @click="selectorOpen = !selectorOpen"
        >
          <div class="min-w-0 flex-1">
            <p class="mt-1 truncate text-base font-semibold text-slate-100">
              {{ selectedNodeSummary() }}
            </p>
            <div class="mt-1 flex items-center gap-2">
              <p class="min-w-0 truncate text-sm text-slate-400">
                {{ selectedAdapterSummary() }}
              </p>
              <span class="min-w-0 truncate text-sm text-slate-400"> /</span>
              <p class="min-w-0 flex-1 truncate text-sm text-slate-400">
                {{ selectedNodeBadge() }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              class="rounded-[1.1rem] border border-white/8 bg-white/5 px-3 py-2 text-left transition-transform duration-200 ease-out active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="selectedAdapter == null || dashboardLoading"
              @click.stop="openSelectedAdapterSettings"
            >
              <Settings2 :size="18" class="shrink-0 text-slate-300" />
            </button>
            <template v-if="nodes.length > 1">
              <ChevronRight
                :size="18"
                class="shrink-0 text-slate-500 transition-transform duration-200"
                :class="selectorOpen ? 'rotate-90' : 'rotate-0'"
              />
            </template>
          </div>
        </button>

        <Transition
          enter-active-class="transition duration-220 ease-out"
          enter-from-class="opacity-0 -translate-y-2"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-180 ease-in"
          leave-from-class="opacity-100 translate-y-0"
          leave-to-class="opacity-0 -translate-y-2"
        >
          <div v-if="selectorOpen" class="mt-3 space-y-2">
            <article
              v-for="node in nodes"
              :key="node.id"
              class="overflow-hidden rounded-[1.4rem] border border-white/8 bg-slate-950/55"
            >
              <template v-if="nodeHasMultipleAdapters(node.id)">
                <header
                  class="flex items-start justify-between gap-3 px-4 pt-4"
                >
                  <div class="min-w-0">
                    <p
                      class="m-0 inline-flex items-center gap-2 text-sm font-semibold text-slate-100"
                    >
                      <Server :size="14" class="text-sky-300" />
                      {{ nodeTitle(node) }}
                    </p>
                    <p class="mt-1 text-xs text-slate-500">
                      {{ nodeSnapshotFor(node.id)?.health?.dbus ?? "Unknown" }}
                      ·
                      {{ nodeSnapshotFor(node.id)?.health?.bluez ?? "Unknown" }}
                    </p>
                  </div>

                  <span
                    class="shrink-0 rounded-full border px-2 py-1 text-[11px]"
                    :class="
                      selectedNodeId === node.id
                        ? 'border-sky-500/30 bg-sky-500/15 text-sky-200'
                        : 'border-white/10 bg-white/5 text-slate-400'
                    "
                  >
                    {{ nodeAdapters(node.id).length }} adapters
                  </span>
                </header>

                <p
                  v-if="nodeSnapshotFor(node.id)?.error"
                  class="px-4 pt-2 text-xs text-rose-300"
                >
                  {{ nodeSnapshotFor(node.id)?.error }}
                </p>

                <div class="px-2 pb-2 pt-3">
                  <template
                    v-for="adapter in nodeAdapters(node.id)"
                    :key="`${node.id}-${adapter.id}`"
                  >
                    <button
                      type="button"
                      class="flex w-full items-center gap-3 rounded-[1.15rem] px-3 py-3 text-left transition-colors duration-200 hover:bg-white/5"
                      :class="
                        selectedNodeId === node.id &&
                        selectedAdapterId === adapter.id
                          ? 'bg-sky-500/10 ring-1 ring-sky-500/20'
                          : ''
                      "
                      @click="selectNodeAdapter(node.id, adapter.id)"
                    >
                      <span
                        class="grid size-8 shrink-0 place-items-center rounded-full border"
                        :class="
                          selectedNodeId === node.id &&
                          selectedAdapterId === adapter.id
                            ? 'border-sky-400/40 bg-sky-500/25 text-sky-100'
                            : 'border-white/10 bg-white/5 text-slate-400'
                        "
                      >
                        <Bluetooth :size="16" />
                      </span>

                      <span class="min-w-0 flex-1">
                        <strong class="block truncate text-sm text-slate-100">
                          {{ adapter.id }}
                        </strong>
                        <span class="block truncate text-xs text-slate-400">
                          {{ adapterTitle(adapter) }}
                        </span>
                      </span>

                      <div
                        class="flex flex-col items-end gap-0 shrink-0 text-xs text-slate-500"
                      >
                        <span>
                          {{ adapter.address }}
                        </span>
                        <template v-if="adapter.discovering">
                          <span> scanning... </span>
                        </template>
                        <template v-else>
                          <span> {{ adapter.device_count }} devices </span>
                        </template>
                      </div>
                    </button>
                  </template>
                </div>
              </template>

              <template v-else>
                <button
                  type="button"
                  class="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors duration-200 hover:bg-white/5 disabled:cursor-not-allowed"
                  :class="
                    selectedNodeId === node.id &&
                    selectedAdapterId === nodeSingleAdapter(node.id)?.id
                      ? 'bg-sky-500/10 ring-1 ring-sky-500/20'
                      : ''
                  "
                  :disabled="nodeSingleAdapter(node.id) == null"
                  @click="
                    nodeSingleAdapter(node.id) != null &&
                    selectNodeAdapter(node.id, nodeSingleAdapter(node.id)!.id)
                  "
                >
                  <span
                    class="grid size-8 shrink-0 place-items-center rounded-full border"
                    :class="
                      selectedNodeId === node.id &&
                      selectedAdapterId === nodeSingleAdapter(node.id)?.id
                        ? 'border-sky-400/40 bg-sky-500/25 text-sky-100'
                        : 'border-white/10 bg-white/5 text-slate-400'
                    "
                  >
                    <Server :size="16" />
                  </span>

                  <span class="min-w-0 flex-1">
                    <strong class="block truncate text-sm text-slate-100">
                      {{ nodeTitle(node) }}
                    </strong>
                    <span class="block truncate text-xs text-slate-400">
                      <template v-if="nodeSingleAdapter(node.id) != null">
                        {{ nodeSingleAdapter(node.id)!.id }}
                        ·
                        {{ adapterTitle(nodeSingleAdapter(node.id)!) }}
                      </template>
                      <template v-else>No adapter available</template>
                    </span>
                    <span class="block truncate text-xs text-slate-500">
                      {{ nodeSnapshotFor(node.id)?.health?.dbus ?? "Unknown" }}
                      ·
                      {{ nodeSnapshotFor(node.id)?.health?.bluez ?? "Unknown" }}
                    </span>
                    <span
                      v-if="nodeSnapshotFor(node.id)?.error"
                      class="block truncate text-xs text-rose-300"
                    >
                      {{ nodeSnapshotFor(node.id)?.error }}
                    </span>
                  </span>

                  <div
                    v-if="nodeSingleAdapter(node.id) != null"
                    class="flex flex-col items-end gap-0 shrink-0 text-xs text-slate-500"
                  >
                    <span>
                      {{ nodeSingleAdapter(node.id)!.address }}
                    </span>
                    <template v-if="nodeSingleAdapter(node.id)!.discovering">
                      <span> scanning... </span>
                    </template>
                    <template v-else>
                      <span>
                        {{ nodeSingleAdapter(node.id)!.device_count }} devices
                      </span>
                    </template>
                  </div>
                </button>
              </template>
            </article>
          </div>
        </Transition>
      </section>

      <template v-if="connectedDevices.length || savedDevices.length">
        <section class="mt-1 flex flex-wrap items-center justify-between gap-2">
          <h2 class="m-0 text-xl font-medium text-slate-300 sm:text-2xl">
            Devices
          </h2>
        </section>
      </template>

      <section class="flex flex-col gap-2">
        <TransitionGroup
          tag="div"
          class="flex flex-col gap-2"
          enter-active-class="transition duration-220 ease-out"
          enter-from-class="opacity-0 translate-y-2 scale-[0.985]"
          enter-to-class="opacity-100 translate-y-0 scale-100"
          leave-active-class="transition duration-160 ease-in"
          leave-from-class="opacity-100 translate-y-0 scale-100"
          leave-to-class="opacity-0 -translate-y-2 scale-[0.985]"
        >
          <template
            v-for="device in connectedDevices"
            :key="`connected-${device.id}`"
          >
            <Item
              class="rounded-[1.4rem] border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-left text-slate-100 shadow-[0_14px_38px_rgba(0,0,0,0.2)] transition-transform duration-200 ease-out active:scale-[0.99]"
              variant="outline"
              size="default"
              as-child
            >
              <button type="button" @click="openDevice(device)">
                <ItemMedia>
                  <span
                    class="grid size-10 shrink-0 place-items-center rounded-full bg-emerald-500/15 text-emerald-200"
                  >
                    <component
                      :is="getDeviceIconComponent(device)"
                      :size="20"
                    />
                  </span>
                </ItemMedia>
                <ItemContent>
                  <ItemTitle class="truncate text-base leading-tight font-bold">
                    {{ deviceTitle(device) }}
                  </ItemTitle>
                  <ItemDescription class="text-xs text-emerald-200/80">
                    {{ deviceStatus(device) }}
                  </ItemDescription>
                </ItemContent>
                <ItemActions>
                  <ChevronRight class="size-4 text-emerald-200/70" />
                </ItemActions>
              </button>
            </Item>
          </template>

          <template v-for="device in savedDevices" :key="`saved-${device.id}`">
            <Item
              class="rounded-[1.4rem] border border-white/8 bg-white/5 px-4 py-3 text-left text-slate-100 shadow-[0_14px_38px_rgba(0,0,0,0.2)] transition-transform duration-200 ease-out active:scale-[0.99]"
              variant="outline"
              size="default"
              as-child
            >
              <button type="button" @click="openDevice(device)">
                <ItemMedia>
                  <span
                    class="grid size-10 shrink-0 place-items-center rounded-full bg-white/8 text-slate-200"
                  >
                    <component
                      :is="getDeviceIconComponent(device)"
                      :size="20"
                    />
                  </span>
                </ItemMedia>
                <ItemContent>
                  <ItemTitle class="truncate text-base leading-tight font-bold">
                    {{ deviceTitle(device) }}
                  </ItemTitle>
                  <ItemDescription class="text-xs text-slate-400">
                    {{ deviceStatus(device) }}
                  </ItemDescription>
                </ItemContent>
                <ItemActions>
                  <ChevronRight class="size-4 text-slate-500" />
                </ItemActions>
              </button>
            </Item>
          </template>
        </TransitionGroup>

        <section class="mt-1 flex flex-wrap items-center justify-between gap-2">
          <h2 class="m-0 text-xl font-medium text-slate-300 sm:text-2xl">
            Available Devices
          </h2>

          <button
            type="button"
            class="grid size-9 place-items-center rounded-full border border-white/10 bg-white/5 text-slate-200 transition-transform duration-200 ease-out active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="selectedAdapter == null || dashboardLoading"
            aria-label="Refresh available devices"
            @click="refreshDashboardAndScan"
          >
            <RefreshCw
              :size="18"
              :class="dashboardLoading ? 'animate-spin' : ''"
            />
          </button>
        </section>

        <template v-if="availableDevices.length === 0">
          <div
            class="rounded-[1.25rem] border border-dashed border-white/10 px-4 py-5 text-sm text-slate-400"
          >
            No available device yet.
          </div>
        </template>
        <template v-else>
          <TransitionGroup
            tag="section"
            class="flex flex-col gap-3"
            enter-active-class="transition duration-220 ease-out"
            enter-from-class="opacity-0 translate-y-2 scale-[0.985]"
            enter-to-class="opacity-100 translate-y-0 scale-100"
            leave-active-class="transition duration-160 ease-in"
            leave-from-class="opacity-100 translate-y-0 scale-100"
            leave-to-class="opacity-0 -translate-y-2 scale-[0.985]"
          >
            <template
              v-for="device in availableDevices"
              :key="`available-${device.id}`"
            >
              <Item
                class="rounded-[1.4rem] border border-white/8 bg-slate-950/55 px-4 py-3 text-left text-slate-100 shadow-[0_14px_38px_rgba(0,0,0,0.2)] transition-transform duration-200 ease-out active:scale-[0.99]"
                variant="outline"
                size="default"
                as-child
              >
                <button type="button" @click="openDevice(device)">
                  <ItemMedia>
                    <span
                      class="grid size-10 shrink-0 place-items-center rounded-full bg-white/8 text-slate-200"
                    >
                      <component
                        :is="getDeviceIconComponent(device)"
                        :size="20"
                      />
                    </span>
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle
                      class="truncate text-base leading-tight font-bold"
                    >
                      {{ deviceTitle(device) }}
                    </ItemTitle>
                    <ItemDescription
                      class="text-xs text-slate-400 empty:hidden"
                      >{{ deviceStatus(device) }}</ItemDescription
                    >
                  </ItemContent>
                  <ItemActions>
                    <ChevronRight class="size-4 text-slate-500" />
                  </ItemActions>
                </button>
              </Item>
            </template>
          </TransitionGroup>
        </template>
      </section>
    </main>

    <footer
      class="flex items-center justify-center w-full bg-slate-950/60 pt-5 text-center text-[8px] font-medium uppercase tracking-[0.28em] text-slate-400 shadow-[0_-10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md transition-all duration-300 ease-out hover:text-slate-200"
    >
      <span
        class="inline-block -translate-y-1 opacity-80 transition-all duration-300 ease-out hover:translate-y-0 hover:opacity-100"
      >
        v{{ appVersion }}
      </span>
    </footer>

    <TooltipProvider>
      <Drawer v-model:open="deviceSheetOpen">
        <DrawerContent v-if="selectedDevice">
          <DrawerHeader>
            <DrawerTitle class="min-w-0 truncate">
              {{ deviceTitle(selectedDevice) }}
            </DrawerTitle>
            <DrawerDescription>
              {{ deviceSubtitle(selectedDevice) }}
            </DrawerDescription>
            <button
              type="button"
              class="absolute top-10 right-4 grid size-8 shrink-0 place-items-center rounded-full border border-white/10 bg-white/5 text-slate-300 transition-transform duration-200 ease-out active:scale-[0.95] disabled:opacity-50"
              :disabled="isRunning('device', selectedDevice.id, 'alias')"
              aria-label="Rename device"
              @click="openSelectedDeviceNameDrawer"
            >
              <Pencil :size="13" />
            </button>
          </DrawerHeader>

          <div class="space-y-3 px-4 pb-4">
            <button
              v-for="action in resolveDeviceDrawerActions(selectedDevice)"
              :key="`${selectedDevice.id}-${action}`"
              type="button"
              class="w-full rounded-[1.1rem] border px-4 py-3 text-sm font-semibold transition-transform duration-200 ease-out active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55"
              :class="deviceActionClass(action)"
              :disabled="isRunning('device', selectedDevice.id, action)"
              @click="handleDeviceActionClick(action)"
            >
              {{ deviceActionLabel(action) }}
            </button>
          </div>
        </DrawerContent>
      </Drawer>

      <Drawer v-model:open="unpairConfirmOpen">
        <DrawerContent v-if="selectedDevice">
          <DrawerHeader>
            <DrawerTitle>Confirm unpair</DrawerTitle>
            <DrawerDescription>
              Unpair {{ deviceTitle(selectedDevice) }} from this adapter?
            </DrawerDescription>
          </DrawerHeader>

          <div class="space-y-3 px-4 pb-4">
            <p class="text-sm text-slate-400">
              This removes the pairing and you may need to pair again before the
              device can reconnect.
            </p>

            <button
              type="button"
              class="w-full rounded-[1.1rem] border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-100 transition-transform duration-200 ease-out active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55"
              :disabled="isRunning('device', selectedDevice.id, 'unpair')"
              @click="confirmUnpairDevice"
            >
              Confirm unpair
            </button>

            <button
              type="button"
              class="w-full rounded-[1.1rem] border border-white/12 bg-white/5 px-4 py-3 text-sm font-semibold text-slate-200 transition-transform duration-200 ease-out active:scale-[0.98]"
              @click="cancelUnpairConfirmation"
            >
              Cancel
            </button>
          </div>
        </DrawerContent>
      </Drawer>

      <Drawer v-model:open="disconnectConfirmOpen">
        <DrawerContent v-if="selectedDevice">
          <DrawerHeader>
            <DrawerTitle>Confirm disconnect</DrawerTitle>
            <DrawerDescription>
              Disconnect {{ deviceTitle(selectedDevice) }} from this adapter?
            </DrawerDescription>
          </DrawerHeader>

          <div class="space-y-3 px-4 pb-4">
            <p class="text-sm text-slate-400">
              This ends the current Bluetooth session. You can reconnect again
              from the device list at any time.
            </p>

            <button
              type="button"
              class="w-full rounded-[1.1rem] border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-100 transition-transform duration-200 ease-out active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55"
              :disabled="isRunning('device', selectedDevice.id, 'disconnect')"
              @click="confirmDisconnectDevice"
            >
              Confirm disconnect
            </button>

            <button
              type="button"
              class="w-full rounded-[1.1rem] border border-white/12 bg-white/5 px-4 py-3 text-sm font-semibold text-slate-200 transition-transform duration-200 ease-out active:scale-[0.98]"
              @click="cancelDisconnectConfirmation"
            >
              Cancel
            </button>
          </div>
        </DrawerContent>
      </Drawer>

      <Drawer v-model:open="adapterSettingsOpen">
        <DrawerContent v-if="selectedAdapter">
          <DrawerHeader>
            <DrawerTitle class="min-w-0 truncate">
              {{ adapterTitle(selectedAdapter) }}
            </DrawerTitle>
            <DrawerDescription>
              {{ selectedNodeSummary() }} · {{ selectedAdapter.id }}
            </DrawerDescription>
            <button
              type="button"
              class="absolute top-10 right-4 grid size-8 shrink-0 place-items-center rounded-full border border-white/10 bg-white/5 text-slate-300 transition-transform duration-200 ease-out active:scale-[0.95] disabled:opacity-50"
              aria-label="Rename adapter"
              @click="openRenameAdapterDrawer"
            >
              <Pencil :size="13" />
            </button>
          </DrawerHeader>

          <div class="space-y-3 px-4 pb-4">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-4 rounded-[1.25rem] border border-white/8 bg-white/5 px-4 py-3 text-left transition-transform duration-200 ease-out active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55"
              :disabled="isRunning('adapter', selectedAdapter.id, 'powered')"
              @click="runAdapterToggle(selectedAdapter, 'powered')"
            >
              <span>
                <span class="block text-sm font-medium text-slate-100"
                  >Power</span
                >
                <span class="block text-xs text-slate-500"
                  >Enable or disable the adapter</span
                >
              </span>
              <span
                class="inline-flex h-8 w-14 items-center rounded-full p-1 transition-colors duration-200"
                :class="selectedAdapter.powered ? 'bg-sky-500' : 'bg-white/10'"
              >
                <span
                  class="size-6 rounded-full bg-white transition-transform duration-200"
                  :class="
                    selectedAdapter.powered ? 'translate-x-6' : 'translate-x-0'
                  "
                />
              </span>
            </button>

            <button
              type="button"
              class="flex w-full items-center justify-between gap-4 rounded-[1.25rem] border border-white/8 bg-white/5 px-4 py-3 text-left transition-transform duration-200 ease-out active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55"
              :disabled="
                isRunning('adapter', selectedAdapter.id, 'discoverable')
              "
              @click="runAdapterToggle(selectedAdapter, 'discoverable')"
            >
              <span>
                <span class="block text-sm font-medium text-slate-100"
                  >Discoverable</span
                >
                <span class="block text-xs text-slate-500"
                  >Allow nearby devices to find it</span
                >
              </span>
              <span
                class="inline-flex h-8 w-14 items-center rounded-full p-1 transition-colors duration-200"
                :class="
                  selectedAdapter.discoverable
                    ? 'bg-emerald-500'
                    : 'bg-white/10'
                "
              >
                <span
                  class="size-6 rounded-full bg-white transition-transform duration-200"
                  :class="
                    selectedAdapter.discoverable
                      ? 'translate-x-6'
                      : 'translate-x-0'
                  "
                />
              </span>
            </button>

            <button
              type="button"
              class="flex w-full items-center justify-between gap-4 rounded-[1.25rem] border border-white/8 bg-white/5 px-4 py-3 text-left transition-transform duration-200 ease-out active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55"
              :disabled="isRunning('adapter', selectedAdapter.id, 'pairable')"
              @click="runAdapterToggle(selectedAdapter, 'pairable')"
            >
              <span>
                <span class="block text-sm font-medium text-slate-100"
                  >Pairable</span
                >
                <span class="block text-xs text-slate-500"
                  >Allow pairing requests</span
                >
              </span>
              <span
                class="inline-flex h-8 w-14 items-center rounded-full p-1 transition-colors duration-200"
                :class="
                  selectedAdapter.pairable ? 'bg-amber-500' : 'bg-white/10'
                "
              >
                <span
                  class="size-6 rounded-full bg-white transition-transform duration-200"
                  :class="
                    selectedAdapter.pairable ? 'translate-x-6' : 'translate-x-0'
                  "
                />
              </span>
            </button>

            <button
              type="button"
              class="flex w-full items-center justify-between gap-4 rounded-[1.25rem] border border-white/8 bg-white/5 px-4 py-3 text-left transition-transform duration-200 ease-out active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55"
              :disabled="
                isRunning(
                  'adapter',
                  selectedAdapter.id,
                  selectedAdapter.discovering ? 'stop-scan' : 'start-scan',
                )
              "
              @click="toggleSelectedAdapterScan"
            >
              <span>
                <span class="block text-sm font-medium text-slate-100">
                  {{ selectedAdapter.discovering ? "Stop scan" : "Start scan" }}
                </span>
                <span class="block text-xs text-slate-500"
                  >Refresh discovery from this adapter</span
                >
              </span>
              <RefreshCw
                :size="18"
                class="text-slate-300"
                :class="selectedAdapter.discovering ? 'animate-spin' : ''"
              />
            </button>
          </div>
        </DrawerContent>
      </Drawer>

      <Drawer v-model:open="deviceNameDrawerOpen">
        <DrawerContent v-if="selectedAdapter">
          <DrawerHeader>
            <div>
              <DrawerTitle>Device name</DrawerTitle>
              <DrawerDescription> Change adapter name. </DrawerDescription>
            </div>
          </DrawerHeader>

          <div class="flex gap-2 px-4 pb-4">
            <InputGroup>
              <InputGroupInput
                maxlength="32"
                placeholder="Device alias"
                :disabled="selectedAdapter == null || dashboardLoading"
                v-model="serverDeviceName"
                @keydown.enter.prevent="saveAdapterName"
              />
              <InputGroupAddon align="inline-end">
                <InputGroupButton
                  variant="secondary"
                  @click="saveAdapterName"
                  :disabled="
                    selectedAdapter == null ||
                    dashboardLoading ||
                    serverDeviceName.trim().length === 0 ||
                    serverDeviceName.trim() ===
                      (selectedAdapter.alias ||
                        selectedAdapter.name ||
                        selectedAdapter.id)
                  "
                >
                  Save
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </div>
        </DrawerContent>
      </Drawer>

      <Drawer v-model:open="selectedDeviceNameDrawerOpen">
        <DrawerContent v-if="selectedDevice">
          <DrawerHeader>
            <div>
              <DrawerTitle>Device Alias</DrawerTitle>
              <DrawerDescription>
                Rename {{ selectedDevice.id }}
              </DrawerDescription>
            </div>
          </DrawerHeader>
          <div class="flex gap-2 px-4 pb-4">
            <InputGroup>
              <InputGroupInput
                maxlength="32"
                placeholder="Adapter Name"
                :disabled="dashboardLoading"
                v-model="selectedDeviceName"
                @keydown.enter.prevent="saveSelectedDeviceName"
              />
              <InputGroupAddon align="inline-end">
                <InputGroupButton
                  variant="secondary"
                  @click="saveSelectedDeviceName"
                  :disabled="
                    dashboardLoading ||
                    selectedDeviceName.trim().length === 0 ||
                    selectedDevice == null ||
                    selectedDeviceName.trim() ===
                      (selectedDevice.alias ||
                        selectedDevice.name ||
                        selectedDevice.id) ||
                    isRunning('device', selectedDevice.id, 'alias')
                  "
                >
                  Save
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </div>
        </DrawerContent>
      </Drawer>
    </TooltipProvider>
    <Toaster />
  </div>
</template>
