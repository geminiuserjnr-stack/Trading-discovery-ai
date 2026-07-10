// Centralized dynamic environment configuration for production-ready deployments

const protocol = window.location.protocol;
const hostname = window.location.hostname;

// Dynamic fallbacks to avoid hardcoding localhost
export const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || `${protocol}//${hostname}:8000`;

const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
export const WS_BASE_URL = (import.meta.env.VITE_WS_URL as string) || `${wsProtocol}//${hostname}:8000`;

console.log(`[Config] Initialized with API_BASE_URL=${API_BASE_URL}, WS_BASE_URL=${WS_BASE_URL}`);
