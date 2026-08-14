export type BlueGateNode = {
  id: string;
  name: string;
  apiBaseUrl: string;
};

type RuntimeConfig = {
  nodes?: BlueGateNode[];
  defaultNodeId?: string;
};

declare global {
  interface Window {
    __BLUEGATE_UI_CONFIG__?: RuntimeConfig;
  }
}

const defaultNodes: BlueGateNode[] = [
  {
    id: "local",
    name: "Local node",
    apiBaseUrl: "http://127.0.0.1:8765",
  },
];

function isValidNode(node: unknown): node is BlueGateNode {
  if (typeof node !== "object" || node === null) {
    return false;
  }

  const candidate = node as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.name === "string" &&
    typeof candidate.apiBaseUrl === "string"
  );
}

export function getRuntimeConfig(): RuntimeConfig {
  return window.__BLUEGATE_UI_CONFIG__ ?? {};
}

export function getNodes(): BlueGateNode[] {
  const config = getRuntimeConfig();
  if (!Array.isArray(config.nodes)) {
    return defaultNodes;
  }

  const nodes = config.nodes.filter(isValidNode);
  return nodes.length > 0 ? nodes : defaultNodes;
}

export function getDefaultNodeId(nodes: BlueGateNode[]): string {
  const config = getRuntimeConfig();
  if (
    config.defaultNodeId &&
    nodes.some((node) => node.id === config.defaultNodeId)
  ) {
    return config.defaultNodeId;
  }

  return nodes[0].id;
}

export function resolveNode(
  nodes: BlueGateNode[],
  selectedNodeId: string,
): BlueGateNode {
  return nodes.find((node) => node.id === selectedNodeId) ?? nodes[0];
}
