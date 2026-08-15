export type BlueGateNode = {
  id: string;
  name: string;
};

const defaultNodes: BlueGateNode[] = [];

function isValidNode(node: unknown): node is BlueGateNode {
  if (typeof node !== "object" || node === null) {
    return false;
  }

  const candidate = node as Record<string, unknown>;
  return typeof candidate.id === "string" && typeof candidate.name === "string";
}

function normalizeOrigin(origin: string): string {
  return origin.endsWith("/") ? origin.slice(0, -1) : origin;
}

export function getNodeProxyBaseUrl(nodeId: string): string {
  return `${normalizeOrigin(window.location.origin)}/${encodeURIComponent(nodeId)}`;
}

export async function loadNodes(): Promise<BlueGateNode[]> {
  try {
    const response = await fetch("/nodes.json", { cache: "no-store" });

    if (!response.ok) {
      return defaultNodes;
    }

    const payload: unknown = await response.json();

    if (!Array.isArray(payload)) {
      return defaultNodes;
    }

    const nodes = payload.filter(isValidNode);
    return nodes.length > 0 ? nodes : defaultNodes;
  } catch {
    return defaultNodes;
  }
}

export function getDefaultNodeId(nodes: BlueGateNode[]): string | undefined {
  return nodes.length ? nodes[0].id : undefined;
}

export function resolveNode(
  nodes: BlueGateNode[],
  selectedNodeId: string,
): BlueGateNode | undefined {
  return nodes.find((node) => node.id === selectedNodeId) ?? nodes[0];
}
