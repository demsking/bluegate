import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import type { Connect } from "vite";
import type { ProxyOptions } from "vite";
import type { PluginOption } from "vite";
import { defineConfig } from "vite";
import { loadEnv } from "vite";

type ConfiguredNode = {
  id: string;
  name: string;
  server: string;
};

function isConfiguredNode(value: unknown): value is ConfiguredNode {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    candidate.id.length > 0 &&
    typeof candidate.name === "string" &&
    candidate.name.length > 0 &&
    typeof candidate.server === "string" &&
    candidate.server.length > 0
  );
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function parseConfiguredNodes(raw: string | undefined): ConfiguredNode[] {
  if (raw == null || raw.trim().length === 0) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(isConfiguredNode);
  } catch {
    return [];
  }
}

function createProxyConfig(
  nodes: ConfiguredNode[],
): Record<string, ProxyOptions> {
  return nodes.reduce<Record<string, ProxyOptions>>((proxy, node) => {
    const escapedId = escapeRegExp(node.id);
    const matchPrefix = new RegExp(`^/${escapedId}(?=/|$)`);

    proxy[`^/${escapedId}(?=/|$)`] = {
      target: node.server,
      changeOrigin: true,
      ws: true,
      secure: false,
      rewrite: (path) => path.replace(matchPrefix, ""),
    };

    return proxy;
  }, {});
}

function nodesJsonPlugin(nodes: ConfiguredNode[]): PluginOption {
  const payload = JSON.stringify(nodes);

  return {
    name: "bluegate-nodes-json",
    configureServer(server) {
      const middleware: Connect.NextHandleFunction = (req, res, next) => {
        if (req.url !== "/nodes.json") {
          next();
          return;
        }

        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.setHeader("Cache-Control", "no-store");
        res.end(payload);
      };

      server.middlewares.use(middleware);
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const configuredNodes = parseConfiguredNodes(env.BLUEGATE_NODES_JSON);

  return {
    plugins: [vue(), tailwindcss(), nodesJsonPlugin(configuredNodes)],
    resolve: {
      alias: {
        "@": new URL("./src", import.meta.url).pathname,
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: createProxyConfig(configuredNodes),
    },
  };
});
