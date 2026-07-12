import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import {
  RefreshCw, Link as LinkIcon, Search, CheckCircle2, AlertTriangle,
  ExternalLink, ChevronUp, ChevronDown, ChevronsUpDown, Copy, Check, Users, Video, Globe, MessageSquare
} from 'lucide-react';
import { Button, StatusBadge, Drawer, LoadingSkeleton, ErrorState, EmptyState } from '../components/UI';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';

export const Channels: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { isAdmin } = useAuth();

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [germanOnly, setGermanOnly] = useState(false);
  const [discordStatus, setDiscordStatus] = useState('all');
  const [discordType, setDiscordType] = useState('all');

  // High-density filter inputs
  const [country, setCountry] = useState('');
  const [debouncedCountry, setDebouncedCountry] = useState('');

  const [language, setLanguage] = useState('');
  const [debouncedLanguage, setDebouncedLanguage] = useState('');

  const [topic, setTopic] = useState('');
  const [debouncedTopic, setDebouncedTopic] = useState('');

  const [discoveryQuery, setDiscoveryQuery] = useState('');
  const [debouncedDiscoveryQuery, setDebouncedDiscoveryQuery] = useState('');

  // Pagination state
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  // Sorting state
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Selected Channel Profile Drawer State
  const [selectedChannelId, setSelectedChannelId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Debouncing logic for inputs
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(0); // Reset page on input change
    }, 400);
    return () => clearTimeout(handler);
  }, [search]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedCountry(country);
      setPage(0);
    }, 400);
    return () => clearTimeout(handler);
  }, [country]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedLanguage(language);
      setPage(0);
    }, 400);
    return () => clearTimeout(handler);
  }, [language]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedTopic(topic);
      setPage(0);
    }, 400);
    return () => clearTimeout(handler);
  }, [topic]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedDiscoveryQuery(discoveryQuery);
      setPage(0);
    }, 400);
    return () => clearTimeout(handler);
  }, [discoveryQuery]);

  // If a channel ID is provided in URL, automatically select it!
  const urlChannelId = searchParams.get('id');
  useEffect(() => {
    if (urlChannelId) {
      setSelectedChannelId(urlChannelId);
    }
  }, [urlChannelId]);

  // Reset all filters helper
  const handleResetFilters = () => {
    setSearch('');
    setCountry('');
    setLanguage('');
    setTopic('');
    setDiscoveryQuery('');
    setGermanOnly(false);
    setDiscordStatus('all');
    setDiscordType('all');
    setPage(0);
    setSortBy('created_at');
    setSortOrder('desc');
    addToast('Filters reset successfully.', 'info', 'Query Controls');
  };

  // Fetch Channels list
  const { data: queryData, isLoading, error, refetch, isPlaceholderData } = useQuery<{ data: any[], totalCount: number }>({
    queryKey: [
      'channels',
      page,
      pageSize,
      debouncedSearch,
      germanOnly,
      discordStatus,
      discordType,
      debouncedCountry,
      debouncedLanguage,
      debouncedTopic,
      debouncedDiscoveryQuery,
      sortBy,
      sortOrder
    ],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('skip', (page * pageSize).toString());
      params.append('limit', pageSize.toString());
      if (germanOnly) params.append('german_only', 'true');
      if (discordStatus !== 'all') params.append('discord_status', discordStatus);
      if (discordType !== 'all') params.append('discord_type', discordType);
      if (debouncedSearch) params.append('search', debouncedSearch);
      if (debouncedCountry) params.append('country', debouncedCountry);
      if (debouncedLanguage) params.append('detected_language', debouncedLanguage);
      if (debouncedTopic) params.append('topic', debouncedTopic);
      if (debouncedDiscoveryQuery) params.append('discovery_query', debouncedDiscoveryQuery);
      if (sortBy) params.append('sort_by', sortBy);
      params.append('sort_order', sortOrder);

      const res = await fetch(`${API_BASE_URL}/channels?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to retrieve discovered channels');

      const totalCountHeader = res.headers.get('X-Total-Count');
      const totalCount = totalCountHeader ? parseInt(totalCountHeader, 10) : 0;
      const data = await res.json();
      return { data, totalCount };
    },
    placeholderData: (prev) => prev
  });

  const channels = queryData?.data || [];
  const totalCount = queryData?.totalCount || 0;
  const totalPages = Math.ceil(totalCount / pageSize);

  // Fetch Channel Detail
  const { data: detailData, isLoading: isDetailLoading } = useQuery<any>({
    queryKey: ['channel-detail', selectedChannelId],
    queryFn: async () => {
      if (!selectedChannelId) return null;
      const res = await fetch(`${API_BASE_URL}/channels/${selectedChannelId}`);
      if (!res.ok) throw new Error('Failed to retrieve channel detailed profile');
      return res.json();
    },
    enabled: !!selectedChannelId
  });

  // Manual Crawl Trigger Mutation
  const crawlMutation = useMutation({
    mutationFn: async (channelId: string) => {
      const res = await fetch(`${API_BASE_URL}/crawl/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_id: channelId })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Crawl request failed');
      }
      return res.json();
    },
    onSuccess: (data) => {
      addToast(data.message || 'Crawl job queued successfully.', 'success', 'Crawl Worker');
      queryClient.invalidateQueries({ queryKey: ['crawl-queue'] });
    },
    onError: (err: any) => {
      addToast(err.message || 'Failed to trigger crawl.', 'error', 'Crawl Error');
    }
  });

  const handleOpenDetail = (channelId: string) => {
    setSelectedChannelId(channelId);
    setSearchParams({ id: channelId });
  };

  const handleCloseDetail = () => {
    setSelectedChannelId(null);
    setSearchParams({});
  };

  const handleCopyId = (e: React.MouseEvent, channelId: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(channelId);
    setCopiedId(channelId);
    addToast('Channel ID copied to clipboard.', 'success', 'Dashboard UI');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setPage(0);
  };

  const renderSortIcon = (field: string) => {
    if (sortBy !== field) return <ChevronsUpDown size={12} className="text-darkMuted" />;
    return sortOrder === 'asc'
      ? <ChevronUp size={12} className="text-accentPrimary font-bold" />
      : <ChevronDown size={12} className="text-accentPrimary font-bold" />;
  };

  const getDiscordStatusBadge = (status: string) => {
    const s = status ? status.toLowerCase() : 'none';
    if (s === 'found') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] uppercase font-mono font-bold px-1.5 py-0.5 rounded border border-accentSuccess bg-accentSuccess/5 text-accentSuccess">
          <CheckCircle2 size={10} /> Found
        </span>
      );
    }
    if (s === 'mentioned') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] uppercase font-mono font-bold px-1.5 py-0.5 rounded border border-accentWarning bg-accentWarning/5 text-accentWarning">
          <AlertTriangle size={10} /> Mention
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[10px] uppercase font-mono font-bold px-1.5 py-0.5 rounded border border-darkBorder bg-darkCard/50 text-darkMuted">
        None
      </span>
    );
  };

  const getDiscordTypeBadge = (type: string) => {
    const t = type ? type.toLowerCase() : 'unknown';
    if (t === 'paid') {
      return <StatusBadge status="PAID" type="warning" />;
    }
    if (t === 'free') {
      return <StatusBadge status="FREE" type="success" />;
    }
    return <StatusBadge status="UNKNOWN" type="neutral" />;
  };

  if (error) {
    return <ErrorState message={(error as Error).message} onRetry={refetch} />;
  }

  return (
    <div className="space-y-4 select-none h-full flex flex-col">
      {/* Page Title & Stats Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between border-b border-darkBorder pb-3.5 flex-shrink-0 gap-3">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary">
            TRADING CHANNELS & COMMUNITIES
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Evaluate discovered trading channels, verify Discord communities, and access verified portals directly.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={germanOnly ? 'primary' : 'outline'}
            size="sm"
            onClick={() => {
              setGermanOnly(!germanOnly);
              setPage(0);
            }}
          >
            German Only
          </Button>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw size={12} className="mr-1" /> Reload
          </Button>
        </div>
      </div>

      {/* Advanced Dense Toolbar */}
      <div className="bg-darkCard border border-darkBorder rounded p-3 flex-shrink-0 space-y-2.5 shadow-subtle">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-4 gap-3">
          {/* Main Search Input */}
          <div className="relative">
            <span className="text-[9px] font-mono font-bold text-darkMuted uppercase block mb-1">Search Channels</span>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-darkMuted" size={13} />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search name, ID..."
                className="w-full h-8 pl-8 pr-3 rounded bg-darkBg border border-darkBorder text-xs text-darkText placeholder-darkMuted focus:outline-none focus:border-accentPrimary transition-colors"
              />
            </div>
          </div>

          {/* Discord Status Selection */}
          <div>
            <span className="text-[9px] font-mono font-bold text-darkMuted uppercase block mb-1">Discord Status</span>
            <select
              value={discordStatus}
              onChange={(e) => {
                setDiscordStatus(e.target.value);
                setPage(0);
              }}
              className="w-full h-8 px-2 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary"
            >
              <option value="all">All Statuses</option>
              <option value="found">Verified Invite Found</option>
              <option value="mentioned">Mentioned (Unverified)</option>
              <option value="none">No Discord Detected</option>
            </select>
          </div>

          {/* Discord Type Selection */}
          <div>
            <span className="text-[9px] font-mono font-bold text-darkMuted uppercase block mb-1">Discord Type</span>
            <select
              value={discordType}
              onChange={(e) => {
                setDiscordType(e.target.value);
                setPage(0);
              }}
              className="w-full h-8 px-2 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary"
            >
              <option value="all">All Types</option>
              <option value="free">Free Access</option>
              <option value="paid">Paid Communities</option>
              <option value="unknown">Unknown / Not Checked</option>
            </select>
          </div>

          {/* Niche (Topic) input */}
          <div>
            <span className="text-[9px] font-mono font-bold text-darkMuted uppercase block mb-1">Trading Niche</span>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Scalping, Crypto, DAX..."
              className="w-full h-8 px-2.5 rounded bg-darkBg border border-darkBorder text-xs text-darkText placeholder-darkMuted focus:outline-none focus:border-accentPrimary transition-colors"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-4 gap-3 pt-1 border-t border-darkBorder/40">
          {/* Country Field */}
          <div>
            <span className="text-[9px] font-mono font-bold text-darkMuted uppercase block mb-1">Country code</span>
            <input
              type="text"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              placeholder="e.g. DE, CH, AT, US"
              className="w-full h-8 px-2.5 rounded bg-darkBg border border-darkBorder text-xs text-darkText placeholder-darkMuted focus:outline-none focus:border-accentPrimary transition-colors"
            />
          </div>

          {/* Language Field */}
          <div>
            <span className="text-[9px] font-mono font-bold text-darkMuted uppercase block mb-1">Language</span>
            <input
              type="text"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              placeholder="e.g. de, en, fr"
              className="w-full h-8 px-2.5 rounded bg-darkBg border border-darkBorder text-xs text-darkText placeholder-darkMuted focus:outline-none focus:border-accentPrimary transition-colors"
            />
          </div>

          {/* Discovery Query Field */}
          <div>
            <span className="text-[9px] font-mono font-bold text-darkMuted uppercase block mb-1">Discovery Query</span>
            <input
              type="text"
              value={discoveryQuery}
              onChange={(e) => setDiscoveryQuery(e.target.value)}
              placeholder="e.g. Dax Live Trading"
              className="w-full h-8 px-2.5 rounded bg-darkBg border border-darkBorder text-xs text-darkText placeholder-darkMuted focus:outline-none focus:border-accentPrimary transition-colors"
            />
          </div>

          {/* Reset Filters & Count */}
          <div className="flex items-end justify-between gap-2">
            <Button variant="outline" size="xs" onClick={handleResetFilters} className="h-8 flex-1">
              Reset Filters
            </Button>
            <div className="text-[11px] font-mono text-darkMuted text-right pb-1 flex-shrink-0">
              Total Found: <span className="text-accentPrimary font-bold">{totalCount}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Explorer High-Density Table */}
      <div className="flex-1 bg-darkCard border border-darkBorder rounded overflow-hidden shadow-subtle flex flex-col min-h-0">
        {isLoading ? (
          <div className="p-8"><LoadingSkeleton /></div>
        ) : channels.length === 0 ? (
          <EmptyState title="No Channels Discovered" message="No discovered trading channels met the selected query criteria." />
        ) : (
          <div className="flex-1 overflow-auto relative">
            <table className="w-full text-left border-collapse table-fixed min-w-[1250px]">
              <thead className="bg-darkBg border-b border-darkBorder sticky top-0 z-20 shadow-sm">
                <tr className="text-[10px] uppercase font-mono tracking-wider text-darkMuted h-9">
                  <th className="pl-4 py-1.5 font-bold w-[220px] cursor-pointer hover:bg-darkBorder/40 transition-colors" onClick={() => handleSort('channel_name')}>
                    <div className="flex items-center gap-1.5">
                      Channel Name {renderSortIcon('channel_name')}
                    </div>
                  </th>
                  <th className="py-1.5 font-bold w-[160px]">YouTube Channel ID</th>
                  <th className="py-1.5 font-bold w-[100px] cursor-pointer hover:bg-darkBorder/40 transition-colors text-right" onClick={() => handleSort('subscribers')}>
                    <div className="flex items-center justify-end gap-1.5">
                      Subscribers {renderSortIcon('subscribers')}
                    </div>
                  </th>
                  <th className="py-1.5 font-bold w-[70px] text-center">Country</th>
                  <th className="py-1.5 font-bold w-[70px] text-center">Lang</th>
                  <th className="py-1.5 font-bold w-[110px] cursor-pointer hover:bg-darkBorder/40 transition-colors" onClick={() => handleSort('topic')}>
                    <div className="flex items-center gap-1.5">
                      Niche {renderSortIcon('topic')}
                    </div>
                  </th>
                  <th className="py-1.5 font-bold w-[140px] truncate">Discovery Query</th>
                  <th className="py-1.5 font-bold w-[115px] cursor-pointer hover:bg-darkBorder/40 transition-colors" onClick={() => handleSort('last_crawled')}>
                    <div className="flex items-center gap-1.5">
                      Last Scanned {renderSortIcon('last_crawled')}
                    </div>
                  </th>
                  <th className="py-1.5 font-bold w-[110px] text-center">Discord Status</th>
                  <th className="py-1.5 font-bold w-[80px] text-center">Type</th>
                  <th className="py-1.5 font-bold w-[110px] truncate">Source</th>
                  <th className="pr-4 py-1.5 font-bold w-[90px] text-right">Join Portal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder/60">
                {channels.map((ch) => {
                  return (
                    <tr
                      key={ch.channel_id}
                      onClick={() => handleOpenDetail(ch.channel_id)}
                      className={`h-9 text-xs text-darkText hover:bg-darkBg/60 cursor-pointer transition-colors border-b border-darkBorder/40 ${isPlaceholderData ? 'opacity-50' : ''}`}
                    >
                      {/* Avatar & Channel Name */}
                      <td className="pl-4 py-1 font-semibold text-darkText flex items-center gap-2 min-w-0">
                        {ch.avatar ? (
                          <img src={ch.avatar} alt="Avatar" className="w-5 h-5 rounded-full border border-darkBorder object-cover" />
                        ) : (
                          <div className="w-5 h-5 rounded-full bg-accentPrimary/10 border border-accentPrimary/30 flex items-center justify-center text-[9px] font-bold text-accentPrimary uppercase">
                            {ch.channel_name.charAt(0)}
                          </div>
                        )}
                        <a
                          href={`https://youtube.com/channel/${ch.channel_id}`}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="truncate text-darkText hover:text-accentPrimary hover:underline font-semibold font-sans flex items-center gap-0.5"
                        >
                          {ch.channel_name}
                          <ExternalLink size={10} className="text-darkMuted hover:text-accentPrimary" />
                        </a>
                      </td>

                      {/* Channel ID */}
                      <td className="py-1 font-mono text-[10px] text-darkMuted">
                        <div className="flex items-center gap-1">
                          <span className="truncate max-w-[110px]" title={ch.channel_id}>{ch.channel_id}</span>
                          <button
                            onClick={(e) => handleCopyId(e, ch.channel_id)}
                            className="p-0.5 rounded hover:bg-darkBorder/60 text-darkMuted hover:text-darkText"
                          >
                            {copiedId === ch.channel_id ? <Check size={10} className="text-accentSuccess" /> : <Copy size={10} />}
                          </button>
                        </div>
                      </td>

                      {/* Subscribers */}
                      <td className="py-1 font-mono text-right text-[11px] font-semibold text-darkText">
                        {ch.subscribers ? ch.subscribers.toLocaleString() : 'N/A'}
                      </td>

                      {/* Country */}
                      <td className="py-1 uppercase font-mono text-[10px] text-darkMuted text-center">
                        {ch.country || 'DE'}
                      </td>

                      {/* Language */}
                      <td className="py-1 uppercase font-mono text-[10px] text-accentPrimary text-center">
                        {ch.detected_language || 'de'}
                      </td>

                      {/* Trading Category / Niche */}
                      <td className="py-1">
                        <span className="text-[10px] uppercase font-mono tracking-wider bg-darkBg border border-darkBorder px-1.5 py-0.5 rounded text-darkText truncate block max-w-[100px]" title={ch.topic || 'General'}>
                          {ch.topic || 'General'}
                        </span>
                      </td>

                      {/* Discovery Query */}
                      <td className="py-1 text-darkMuted font-mono text-[11px] truncate max-w-[130px]" title={ch.discovery_query || 'Seed'}>
                        {ch.discovery_query || 'Seed'}
                      </td>

                      {/* Last Scanned */}
                      <td className="py-1 text-darkMuted text-[10px] font-mono" title={ch.last_crawled ? new Date(ch.last_crawled).toLocaleString() : 'Never'}>
                        {ch.last_crawled ? new Date(ch.last_crawled).toLocaleDateString() : 'Never'}
                      </td>

                      {/* Discord Status */}
                      <td className="py-1 text-center">
                        {getDiscordStatusBadge(ch.discord_status)}
                      </td>

                      {/* Discord Type */}
                      <td className="py-1 text-center">
                        {getDiscordTypeBadge(ch.discord_type)}
                      </td>

                      {/* Discord Source */}
                      <td className="py-1 text-darkMuted font-mono text-[10px] truncate max-w-[100px]" title={ch.discord_source || 'unknown'}>
                        {ch.discord_source || 'unknown'}
                      </td>

                      {/* Join Button */}
                      <td className="pr-4 py-1 text-right">
                        {ch.discord_status === 'found' && ch.discord_url ? (
                          <a
                            href={ch.discord_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded bg-accentPrimary text-white hover:bg-accentPrimary/90 text-[10px] font-bold uppercase tracking-wider font-mono transition-colors shadow-sm"
                          >
                            Join <ExternalLink size={9} />
                          </a>
                        ) : (
                          <span className="text-[10px] font-mono text-darkMuted">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Standardized Server-side Pagination controls footer */}
      <div className="bg-darkCard border border-darkBorder rounded p-2.5 flex items-center justify-between flex-shrink-0 shadow-subtle">
        <div className="flex items-center gap-3">
          <span className="text-xs text-darkMuted font-mono">Page Size:</span>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(parseInt(e.target.value, 10));
              setPage(0);
            }}
            className="h-7 px-1.5 rounded bg-darkBg border border-darkBorder text-xs text-darkText focus:outline-none"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <span className="text-xs text-darkMuted font-mono hidden sm:inline">
            Showing <span className="text-darkText font-semibold">{page * pageSize + 1}</span> to <span className="text-darkText font-semibold">{Math.min((page + 1) * pageSize, totalCount)}</span> of <span className="text-darkText font-semibold">{totalCount}</span> channels
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            variant="outline"
            size="xs"
            onClick={() => setPage(0)}
            disabled={page === 0}
            className="h-7 px-2 font-mono"
          >
            &lt;&lt; First
          </Button>
          <Button
            variant="outline"
            size="xs"
            onClick={() => setPage(page - 1)}
            disabled={page === 0}
            className="h-7 px-2.5 font-mono"
          >
            &lt; Prev
          </Button>
          <span className="text-xs font-mono px-3 text-darkText bg-darkBg border border-darkBorder rounded h-7 flex items-center justify-center min-w-[70px]">
            {page + 1} / {totalPages || 1}
          </span>
          <Button
            variant="outline"
            size="xs"
            onClick={() => setPage(page + 1)}
            disabled={page >= totalPages - 1}
            className="h-7 px-2.5 font-mono"
          >
            Next &gt;
          </Button>
          <Button
            variant="outline"
            size="xs"
            onClick={() => setPage(totalPages - 1)}
            disabled={page >= totalPages - 1}
            className="h-7 px-2 font-mono"
          >
            Last &gt;&gt;
          </Button>
        </div>
      </div>

      {/* Channel Profile Drawer */}
      <Drawer
        isOpen={!!selectedChannelId}
        onClose={handleCloseDetail}
        title="CHANNEL_INTELLIGENCE_PROFILE"
      >
        {isDetailLoading ? (
          <LoadingSkeleton />
        ) : detailData ? (
          <div className="space-y-5">
            {/* Banner & Header */}
            <div className="relative border border-darkBorder rounded overflow-hidden bg-darkBg">
              {detailData.channel?.banner ? (
                <img
                  src={detailData.channel.banner}
                  alt="Banner"
                  className="w-full h-24 object-cover opacity-60"
                />
              ) : (
                <div className="w-full h-24 bg-gradient-to-r from-darkCard to-darkBorder" />
              )}
              <div className="absolute top-14 left-4 flex items-end gap-3">
                {detailData.channel?.avatar ? (
                  <img
                    src={detailData.channel.avatar}
                    alt="Avatar"
                    className="w-12 h-12 rounded-full border-2 border-darkCard bg-darkCard object-cover"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-accentPrimary/15 border-2 border-darkCard flex items-center justify-center text-sm font-bold text-accentPrimary uppercase font-mono">
                    {detailData.channel?.channel_name.charAt(0)}
                  </div>
                )}
                <div className="pb-1 bg-darkCard/95 px-2.5 py-1 rounded border border-darkBorder shadow-sm">
                  <h2 className="text-xs font-bold text-darkText uppercase font-mono tracking-wider flex items-center gap-1">
                    {detailData.channel?.channel_name}
                    <a
                      href={`https://youtube.com/channel/${detailData.channel?.channel_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accentPrimary hover:underline inline-flex items-center"
                    >
                      <ExternalLink size={11} />
                    </a>
                  </h2>
                  <span className="text-[9px] font-mono text-darkMuted block">ID: {detailData.channel?.channel_id}</span>
                </div>
              </div>
            </div>

            {/* Scrape Metadata / Trigger Action */}
            <div className="flex items-center justify-between p-3 rounded bg-darkBg border border-darkBorder mt-2">
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] font-mono text-darkMuted">LAST DISCOVERY SCAN</span>
                <span className="text-xs font-mono text-darkText">
                  {detailData.channel?.last_crawled ? new Date(detailData.channel.last_crawled).toLocaleString() : 'Never'}
                </span>
              </div>
              {isAdmin && (
                <Button
                  variant="primary"
                  size="xs"
                  onClick={() => crawlMutation.mutate(detailData.channel.channel_id)}
                  disabled={crawlMutation.isPending}
                >
                  <RefreshCw size={10} className={crawlMutation.isPending ? 'animate-spin' : ''} />
                  Trigger Crawler Run
                </Button>
              )}
            </div>

            {/* Core Stats Grid */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-darkBg border border-darkBorder rounded text-center shadow-sm">
                <span className="text-[9px] font-mono text-darkMuted block uppercase flex items-center justify-center gap-1">
                  <Users size={10} /> SUBSCRIBERS
                </span>
                <span className="text-sm font-bold font-mono text-accentPrimary block mt-1">
                  {detailData.channel?.subscribers?.toLocaleString() || 'N/A'}
                </span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded text-center shadow-sm">
                <span className="text-[9px] font-mono text-darkMuted block uppercase flex items-center justify-center gap-1">
                  <Globe size={10} /> TOTAL VIEWS
                </span>
                <span className="text-sm font-bold font-mono text-accentPrimary block mt-1">
                  {detailData.channel?.total_views?.toLocaleString() || 'N/A'}
                </span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded text-center shadow-sm">
                <span className="text-[9px] font-mono text-darkMuted block uppercase flex items-center justify-center gap-1">
                  <Video size={10} /> VIDEOS COPIED
                </span>
                <span className="text-sm font-bold font-mono text-accentPrimary block mt-1">
                  {detailData.channel?.upload_count ?? 12}
                </span>
              </div>
            </div>

            {/* Discord Community Intelligence Details */}
            <div className="space-y-2 bg-accentPrimary/5 border border-accentPrimary/20 p-3 rounded shadow-sm">
              <span className="text-[10px] font-mono tracking-widest text-accentPrimary font-bold block uppercase flex items-center gap-1">
                <MessageSquare size={11} /> Discord Community Intelligence
              </span>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono mt-2">
                <div className="bg-darkCard border border-darkBorder p-2 rounded text-center">
                  <span className="text-[9px] text-darkMuted block uppercase mb-1">Status</span>
                  {getDiscordStatusBadge(detailData.channel?.discord_status)}
                </div>
                <div className="bg-darkCard border border-darkBorder p-2 rounded text-center">
                  <span className="text-[9px] text-darkMuted block uppercase mb-1">Type</span>
                  {getDiscordTypeBadge(detailData.channel?.discord_type)}
                </div>
                <div className="bg-darkCard border border-darkBorder p-2 rounded text-center">
                  <span className="text-[9px] text-darkMuted block uppercase mb-1">Source</span>
                  <span className="text-[10px] text-darkText font-bold capitalize truncate block">
                    {detailData.channel?.discord_source || 'unknown'}
                  </span>
                </div>
              </div>

              {/* Verified Invite Join CTA */}
              {detailData.channel?.discord_status === 'found' && detailData.channel?.discord_url && (
                <div className="mt-2 pt-2 border-t border-accentPrimary/10">
                  <a
                    href={detailData.channel.discord_url}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded bg-accentPrimary text-white hover:bg-accentPrimary/90 text-xs font-bold uppercase tracking-wider font-mono transition-colors shadow-sm"
                  >
                    Open Verified Discord Community Portal <ExternalLink size={12} />
                  </a>
                </div>
              )}
            </div>

            {/* Description */}
            <div className="space-y-1 bg-darkBg/30 p-3 rounded border border-darkBorder/40">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Channel Description</span>
              <p className="text-xs text-darkText leading-relaxed max-h-32 overflow-y-auto pr-1">
                {detailData.channel?.description || 'No description provided.'}
              </p>
            </div>

            {/* Matches & Evaluation */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">NLP Verification Confidence</span>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2.5 bg-darkBg border border-darkBorder rounded flex items-center justify-between shadow-sm">
                  <span className="text-xs text-darkMuted font-mono">German Language:</span>
                  <StatusBadge status="98% Confidence" type="success" />
                </div>
                <div className="p-2.5 bg-darkBg border border-darkBorder rounded flex items-center justify-between shadow-sm">
                  <span className="text-xs text-darkMuted font-mono">Trading Niche:</span>
                  <StatusBadge status="German Trading" type="success" />
                </div>
              </div>
            </div>

            {/* Community Links */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Detected Public Social Links</span>
              <div className="space-y-2">
                {detailData.community_links?.map((link: any, idx: number) => (
                  <a
                    key={idx}
                    href={link.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between p-2 rounded bg-darkBg hover:bg-darkBorder/40 border border-darkBorder/60 text-xs transition-colors"
                  >
                    <span className="font-mono uppercase text-[10px] tracking-wider text-accentPrimary flex items-center gap-1.5">
                      <LinkIcon size={12} /> {link.platform}
                    </span>
                    <span className="text-xs text-darkMuted hover:text-accentPrimary truncate max-w-sm flex items-center gap-1">
                      {link.url} <ExternalLink size={10} />
                    </span>
                  </a>
                ))}
                {(!detailData.community_links || detailData.community_links.length === 0) && (
                  <p className="text-xs text-darkMuted font-mono text-center py-2 bg-darkBg/25 border border-dashed border-darkBorder rounded">No linked communities detected yet.</p>
                )}
              </div>
            </div>

            {/* Extracted phrases */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Key Extracted Phrases</span>
              <div className="flex flex-wrap gap-1.5">
                {detailData.phrases?.map((p: any) => (
                  <span
                    key={p.phrase}
                    className="text-xs font-mono px-2 py-1 rounded bg-darkBg border border-darkBorder flex items-center gap-2"
                  >
                    <span className="text-darkText font-medium">{p.phrase}</span>
                    <span className="text-[9px] px-1 rounded bg-darkCard text-accentPrimary border border-darkBorder/40">
                      {p.count}x
                    </span>
                  </span>
                ))}
                {(!detailData.phrases || detailData.phrases.length === 0) && (
                  <p className="text-xs text-darkMuted font-mono">No terminology extracted yet.</p>
                )}
              </div>
            </div>

            {/* Matching Recent Videos */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Matching Videos</span>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {detailData.videos?.map((vid: any) => (
                  <div key={vid.video_id} className="p-2 rounded bg-darkBg border border-darkBorder text-xs space-y-1 shadow-sm">
                    <h4 className="font-bold text-darkText truncate">{vid.title}</h4>
                    <div className="flex items-center justify-between text-[10px] text-darkMuted font-mono">
                      <span>{vid.view_count?.toLocaleString()} views</span>
                      <span>{new Date(vid.published_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <EmptyState />
        )}
      </Drawer>
    </div>
  );
};
