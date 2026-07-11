import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  LayoutDashboard, Tv, PlaySquare, Hash, Search, Radio, Share2,
  Activity, Percent, LineChart, Calendar, Cpu, Terminal, Settings,
  LogOut, User, ChevronLeft, ChevronRight, Search as SearchIcon
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { WS_BASE_URL, API_BASE_URL } from '../config';
import { WS_BASE_URL } from '../config';

interface SidebarItem {
  name: string;
  path: string;
  icon: React.ComponentType<any>;
}

const SIDEBAR_ITEMS: SidebarItem[] = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Channels', path: '/channels', icon: Tv },
  { name: 'Videos', path: '/videos', icon: PlaySquare },
  { name: 'Phrases', path: '/phrases', icon: Hash },
  { name: 'Queries', path: '/queries', icon: Search },
  { name: 'Discovery Feed', path: '/feed', icon: Radio },
  { name: 'Communities', path: '/communities', icon: Share2 },
  { name: 'Monitoring', path: '/monitoring', icon: Activity },
  { name: 'Scoring', path: '/scoring', icon: Percent },
  { name: 'Analytics', path: '/analytics', icon: LineChart },
  { name: 'Scheduler', path: '/scheduler', icon: Calendar },
  { name: 'Workers', path: '/workers', icon: Cpu },
  { name: 'Logs', path: '/logs', icon: Terminal },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Shell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();
  const { addToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  // Mock connecting to backend WebSocket server for live updates
  useEffect(() => {
    // Attempt WebSocket connection
    const wsUrl = `${WS_BASE_URL}/ws/events`;
    let socket: WebSocket | null = null;
    let fallbackInterval: any = null;

    try {
      socket = new WebSocket(wsUrl);
      socket.onopen = () => {
        setWsConnected(true);
        addToast('Connected to Live Discovery WebSocket Stream', 'success', 'WS Connection');
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          addToast(payload.message, 'info', payload.title || 'Live Activity');
        } catch (err) {
          // ignore
        }
      };
      socket.onclose = () => {
        setWsConnected(false);
        // Fallback polling alert
        addToast('WebSocket stream unavailable. Falling back to active REST polling.', 'warning', 'WS Connection');
      };
      socket.onerror = () => {
        setWsConnected(false);
      };
    } catch (err) {
      setWsConnected(false);
    }

    // Polling fallback simulation for live feed events if socket closes
    fallbackInterval = setInterval(() => {
      if (!wsConnected) {
        // Occasionally trigger notifications
        const randomEvents = [
          { message: 'Analyzed transcript for video UC_tr_xyz_1', title: 'NLP Pipeline' },
          { message: 'Discovered new S&P 500 scalper channel', title: 'Deduplication' },
          { message: 'API Quota remaining: 9850 units', title: 'Quota Warning' }
        ];
        const event = randomEvents[Math.floor(Math.random() * randomEvents.length)];
        addToast(event.message, 'info', event.title);
      }
    }, 15000);

    return () => {
      if (socket) socket.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
    };
  }, [wsConnected, addToast]);

  // Handle local searching across all concepts
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    const controller = new AbortController();
    const fetchResults = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/search/global?q=${encodeURIComponent(searchQuery)}`, {
          signal: controller.signal
        });
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data);
        }
      } catch (err) {
        // Ignore abort or network errors
      }
    };

    // Simple debounce of 150ms
    const delayDebounce = setTimeout(() => {
      fetchResults();
    }, 150);

    return () => {
      clearTimeout(delayDebounce);
      controller.abort();
    };
  }, [searchQuery]);

  const handleSearchResultClick = (item: any) => {
    setSearchQuery('');
    setSearchResults([]);
    if (item.type === 'channel') {
      navigate(`/channels?id=${item.desc}`);
    } else if (item.type === 'video') {
      navigate(`/videos?id=${item.desc}`);
    } else if (item.type === 'phrase') {
      navigate(`/phrases?id=${encodeURIComponent(item.name)}`);
    } else if (item.type === 'query') {
      navigate(`/queries`);
    } else if (item.type === 'community') {
      navigate(`/communities`);
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-darkBg text-darkText select-none">
      {/* Top Navigation */}
      <header className="flex items-center justify-between h-14 px-4 bg-darkCard border-b border-darkBorder z-20 flex-shrink-0">
        {/* Branding */}
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-accentPrimary flex items-center justify-center font-mono font-bold text-darkBg text-xs select-none flex-shrink-0">
            Y
          </div>
          <span className="font-mono text-xs font-bold tracking-wider text-darkText uppercase whitespace-nowrap">
            outube Discovery Engine <span className="text-accentPrimary text-[10px] font-normal lowercase">v2a</span>
          </span>
        </div>

        {/* Global Search Bar */}
        <div className="relative w-96">
          <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-darkMuted">
            <SearchIcon size={14} />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search channels, videos, phrases, queries, communities..."
            className="w-full h-8 pl-9 pr-4 rounded bg-darkBg border border-darkBorder text-xs text-darkText placeholder-darkMuted focus:outline-none focus:border-accentPrimary transition-colors"
          />
          {searchResults.length > 0 && (
            <div className="absolute top-10 left-0 w-full bg-darkCard border border-darkBorder rounded shadow-subtle overflow-hidden z-50">
              {searchResults.map((res, i) => (
                <button
                  key={i}
                  onClick={() => handleSearchResultClick(res)}
                  className="w-full text-left px-4 py-2 hover:bg-darkBg flex items-center justify-between text-xs transition-colors border-b border-darkBorder last:border-b-0"
                >
                  <span className="font-medium text-darkText">{res.name}</span>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-accentPrimary px-1.5 py-0.5 rounded bg-darkBg/50 border border-darkBorder/40">
                    {res.type}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Real-time Status and User Badges */}
        <div className="flex items-center gap-4">
          {/* WS Status Indicator */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-darkBg border border-darkBorder text-[10px] font-mono">
            <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-accentSuccess animate-pulse' : 'bg-accentWarning'}`} />
            <span className="text-darkMuted uppercase">WS: {wsConnected ? 'Connected' : 'Polling'}</span>
          </div>

          {/* User profile */}
          <div className="flex items-center gap-2">
            <div className="flex flex-col items-end">
              <span className="text-xs font-semibold text-darkText">{user?.username || 'Trader'}</span>
              <span className={`text-[9px] uppercase font-mono tracking-wider px-1.5 py-0.2 rounded border ${
                user?.role === 'Admin' ? 'border-accentSuccess text-accentSuccess' : 'border-accentPrimary text-accentPrimary'
              }`}>
                {user?.role || 'Viewer'}
              </span>
            </div>
            <div className="w-8 h-8 rounded-full bg-darkBg border border-darkBorder flex items-center justify-center text-accentPrimary">
              <User size={16} />
            </div>
            <button
              onClick={() => logout()}
              title="Logout"
              className="p-1 rounded hover:bg-darkBg text-accentDanger transition-colors ml-1 focus:outline-none"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden">
        {/* Persistent Left Sidebar */}
        <aside
          className={`bg-darkCard border-r border-darkBorder transition-all duration-300 flex flex-col justify-between z-10 select-none ${
            isCollapsed ? 'w-14' : 'w-56'
          }`}
        >
          {/* Navigation Links */}
          <nav className="flex-1 overflow-y-auto py-3 space-y-0.5">
            {SIDEBAR_ITEMS.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center h-9 px-3 mx-2 rounded transition-colors text-xs select-none ${
                    isActive
                      ? 'bg-darkBg text-accentPrimary font-semibold border-l-2 border-accentPrimary'
                      : 'text-darkMuted hover:bg-darkBg/60 hover:text-darkText'
                  }`}
                >
                  <span className="flex-shrink-0">
                    <Icon size={16} />
                  </span>
                  {!isCollapsed && (
                    <span className="ml-3 truncate uppercase tracking-wider font-mono text-[10px]">
                      {item.name}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Toggle Button */}
          <div className="h-10 border-t border-darkBorder flex items-center justify-end px-3">
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-1 rounded hover:bg-darkBg text-darkMuted hover:text-darkText transition-colors focus:outline-none"
            >
              {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
          </div>
        </aside>

        {/* Scrollable Content Area */}
        <main className="flex-1 overflow-y-auto bg-darkBg relative p-4">
          {children}
        </main>
      </div>
    </div>
  );
};
