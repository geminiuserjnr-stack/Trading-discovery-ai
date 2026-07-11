// Centralized dynamic environment configuration for production-ready deployments

const protocol = window.location.protocol;
const hostname = window.location.hostname;

// Under Vite, client env variables must be prefixed with VITE_ and are inlined at build time.
let apiBase = import.meta.env.VITE_API_URL as string;
let wsBase = import.meta.env.VITE_WS_URL as string;

if (!apiBase) {
  // If no env is configured, resolve dynamically
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    // Local development fallback
    apiBase = `${protocol}//${hostname}:8000`;
  } else {
    // Production fallback: If on Railway as a monorepo / single domain, or same-origin routing
    apiBase = `${protocol}//${hostname}`;
  }
}

if (!wsBase) {
  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    wsBase = `${wsProtocol}//${hostname}:8000`;
  } else {
    wsBase = `${wsProtocol}//${hostname}`;
  }
}

export const API_BASE_URL = apiBase;
export const WS_BASE_URL = wsBase;

console.log(`[Config] Initialized with API_BASE_URL=${API_BASE_URL}, WS_BASE_URL=${WS_BASE_URL}`);
