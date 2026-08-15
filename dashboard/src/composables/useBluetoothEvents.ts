import { onBeforeUnmount, ref } from "vue";
import type { BluetoothEvent } from "@/types/events";

function toWebsocketUrl(baseUrl: string) {
  const url = new URL(baseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const normalizedPath = url.pathname.replace(/\/$/, "");
  url.pathname = normalizedPath.endsWith("/api")
    ? `${normalizedPath}/ws/`
    : `${normalizedPath}/api/ws/`;
  return url.toString();
}

export function useBluetoothEvents(onEvent: (event: BluetoothEvent) => void) {
  const connected = ref(false);
  const reconnecting = ref(false);
  const lastMessageAt = ref<string | null>(null);

  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let activeBaseUrl: string | null = null;

  const connect = (baseUrl: string) => {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    if (socket) {
      socket.close();
      socket = null;
    }

    activeBaseUrl = baseUrl;
    const wsUrl = toWebsocketUrl(baseUrl);
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      connected.value = true;
      reconnecting.value = false;
    };

    socket.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as BluetoothEvent;
        lastMessageAt.value = new Date().toISOString();
        if (event.type !== "ping") {
          onEvent(event);
        }
      } catch {
        // Ignore malformed event payloads.
      }
    };

    socket.onclose = () => {
      connected.value = false;
      reconnecting.value = true;
      reconnectTimer = window.setTimeout(() => {
        if (activeBaseUrl) {
          connect(activeBaseUrl);
        }
      }, 1800);
    };

    socket.onerror = () => {
      socket?.close();
    };
  };

  const disconnect = () => {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    reconnecting.value = false;
    connected.value = false;
    socket?.close();
    socket = null;
  };

  onBeforeUnmount(disconnect);

  return {
    connect,
    disconnect,
    connected,
    reconnecting,
    lastMessageAt,
  };
}
