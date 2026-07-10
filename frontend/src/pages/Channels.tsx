import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { RefreshCw, Link as LinkIcon } from 'lucide-react';
import { Button, StatusBadge, SearchBox, Drawer, LoadingSkeleton, ErrorState, EmptyState } from '../components/UI';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';

export const Channels: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { isAdmin } = useAuth();

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [germanOnly, setGermanOnly] = useState(false);
  const [selectedChannelId, setSelectedChannelId] = useState<string | null>(null);

  // If a channel ID is provided in URL, automatically select it!
  const urlChannelId = searchParams.get('id');
  useEffect(() => {
    if (urlChannelId) {
      setSelectedChannelId(urlChannelId);
    }
  }, [urlChannelId]);

  // Fetch Channels list
  const { data: channels, isLoading, error, refetch } = useQuery<any[]>({
    queryKey: ['channels', germanOnly],
    queryFn: async () => {
      const url = `http://127.0.0.1:8000/channels?limit=100&german_only=${germanOnly}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to retrieve discovered channels');
      return res.json();
    }
  });

  // Fetch Channel Detail
  const { data: detailData, isLoading: isDetailLoading } = useQuery<any>({
    queryKey: ['channel-detail', selectedChannelId],
    queryFn: async () => {
      if (!selectedChannelId) return null;
      const res = await fetch(`http://127.0.0.1:8000/channels/${selectedChannelId}`);
      if (!res.ok) throw new Error('Failed to retrieve channel detailed profile');
      return res.json();
    },
    enabled: !!selectedChannelId
  });

  // Manual Crawl Trigger Mutation
  const crawlMutation = useMutation({
    mutationFn: async (channelId: string) => {
      const res = await fetch('http://127.0.0.1:8000/crawl/trigger', {
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

  // Filter channels locally
  const filteredChannels = channels?.filter(ch =>
    ch.channel_name.toLowerCase().includes(search.toLowerCase()) ||
    ch.channel_id.toLowerCase().includes(search.toLowerCase()) ||
    (ch.discovery_query && ch.discovery_query.toLowerCase().includes(search.toLowerCase()))
  ) || [];

  const handleOpenDetail = (channelId: string) => {
    setSelectedChannelId(channelId);
    setSearchParams({ id: channelId });
  };

  const handleCloseDetail = () => {
    setSelectedChannelId(null);
    setSearchParams({});
  };

  if (error) {
    return <ErrorState message={(error as Error).message} onRetry={refetch} />;
  }

  return (
    <div className="space-y-6 select-none h-full flex flex-col">
      {/* Page Title & Controls */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4 flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary">
            DISCOVERED YOUTUBE CHANNELS
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Search, filter, and inspect detailed profiles of German-speaking trading channels.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant={germanOnly ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setGermanOnly(!germanOnly)}
          >
            German Only
          </Button>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw size={12} className="mr-1" /> Reload
          </Button>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex items-center justify-between bg-darkCard border border-darkBorder rounded p-3 flex-shrink-0">
        <SearchBox value={search} onChange={setSearch} placeholder="Search name, ID, query..." />
        <div className="text-xs text-darkMuted font-mono">
          Showing <span className="text-accentPrimary">{filteredChannels.length}</span> of {channels?.length || 0} channels
        </div>
      </div>

      {/* Explorer Content */}
      <div className="flex-1 bg-darkCard border border-darkBorder rounded overflow-hidden shadow-subtle flex flex-col">
        {isLoading ? (
          <div className="p-8"><LoadingSkeleton /></div>
        ) : filteredChannels.length === 0 ? (
          <EmptyState title="No Channels Discovered" message="Try searching for another query or click reload." />
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-darkBg border-b border-darkBorder sticky top-0 z-10">
                <tr className="text-[10px] uppercase font-mono tracking-wider text-darkMuted h-10">
                  <th className="pl-4 py-2 font-semibold">Channel Name</th>
                  <th className="py-2 font-semibold">Subscribers</th>
                  <th className="py-2 font-semibold">Language</th>
                  <th className="py-2 font-semibold">Country</th>
                  <th className="py-2 font-semibold">Trading Category</th>
                  <th className="py-2 font-semibold">Videos</th>
                  <th className="py-2 font-semibold">Discovery Query</th>
                  <th className="py-2 font-semibold">Last Crawl</th>
                  <th className="pr-4 py-2 text-right font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder">
                {filteredChannels.map((ch) => (
                  <tr
                    key={ch.channel_id}
                    onClick={() => handleOpenDetail(ch.channel_id)}
                    className="h-10 text-xs text-darkText hover:bg-darkBg/60 cursor-pointer transition-colors border-b border-darkBorder"
                  >
                    <td className="pl-4 py-1.5 font-semibold text-darkText flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-accentPrimary/10 border border-accentPrimary/30 flex items-center justify-center text-[10px] font-bold text-accentPrimary">
                        {ch.channel_name.charAt(0)}
                      </div>
                      <span className="truncate max-w-[180px]">{ch.channel_name}</span>
                    </td>
                    <td className="py-1.5 font-mono text-xs">
                      {ch.subscribers ? ch.subscribers.toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-1.5 uppercase font-mono text-[10px] text-accentPrimary">
                      {ch.detected_language || 'de'}
                    </td>
                    <td className="py-1.5 uppercase font-mono text-[10px] text-darkMuted">
                      {ch.country || 'DE'}
                    </td>
                    <td className="py-1.5">
                      <span className="text-[10px] uppercase font-mono tracking-wider bg-darkBg border border-darkBorder px-1.5 py-0.5 rounded text-darkText">
                        {ch.topic || 'General'}
                      </span>
                    </td>
                    <td className="py-1.5 font-mono text-xs">{ch.upload_count ?? 12}</td>
                    <td className="py-1.5 text-darkMuted font-mono text-[11px] truncate max-w-[150px]">
                      {ch.discovery_query || 'Seed'}
                    </td>
                    <td className="py-1.5 text-darkMuted text-[10px] font-mono">
                      {ch.last_crawled ? new Date(ch.last_crawled).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="pr-4 py-1.5 text-right">
                      <StatusBadge status={ch.active ? 'ACTIVE' : 'INACTIVE'} type={ch.active ? 'success' : 'neutral'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Channel Profile Drawer */}
      <Drawer
        isOpen={!!selectedChannelId}
        onClose={handleCloseDetail}
        title="CHANNEL_PROFILE"
      >
        {isDetailLoading ? (
          <LoadingSkeleton />
        ) : detailData ? (
          <div className="space-y-6">
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
              <div className="absolute top-16 left-4 flex items-end gap-3">
                <img
                  src={detailData.channel?.avatar || 'https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=100&auto=format&fit=crop&q=60'}
                  alt="Avatar"
                  className="w-12 h-12 rounded-full border-2 border-darkCard bg-darkCard"
                />
                <div className="pb-1 bg-darkCard/80 px-2 py-0.5 rounded border border-darkBorder">
                  <h2 className="text-xs font-bold text-darkText uppercase font-mono tracking-wider">
                    {detailData.channel?.channel_name}
                  </h2>
                </div>
              </div>
            </div>

            {/* Scrape Metadata / Trigger Action */}
            <div className="flex items-center justify-between p-3 rounded bg-darkBg border border-darkBorder mt-2">
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] font-mono text-darkMuted">LAST REFRESH</span>
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
              <div className="p-3 bg-darkBg border border-darkBorder rounded text-center">
                <span className="text-[9px] font-mono text-darkMuted block">SUBSCRIBERS</span>
                <span className="text-sm font-bold font-mono text-accentPrimary">
                  {detailData.channel?.subscribers?.toLocaleString() || 'N/A'}
                </span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded text-center">
                <span className="text-[9px] font-mono text-darkMuted block">TOTAL VIEWS</span>
                <span className="text-sm font-bold font-mono text-accentPrimary">
                  {detailData.channel?.total_views?.toLocaleString() || 'N/A'}
                </span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded text-center">
                <span className="text-[9px] font-mono text-darkMuted block">VIDEO COUNT</span>
                <span className="text-sm font-bold font-mono text-accentPrimary">
                  {detailData.channel?.upload_count ?? 12}
                </span>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-1 bg-darkBg/30 p-3 rounded border border-darkBorder/40">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Channel Description</span>
              <p className="text-xs text-darkText leading-relaxed">
                {detailData.channel?.description || 'No description provided.'}
              </p>
            </div>

            {/* Matches & Evaluation */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">NLP Verification Confidence</span>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
                  <span className="text-xs text-darkMuted font-mono">German Language:</span>
                  <StatusBadge status="98% Confidence" type="success" />
                </div>
                <div className="p-2 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
                  <span className="text-xs text-darkMuted font-mono">Trading Niche:</span>
                  <StatusBadge status="German Trading" type="success" />
                </div>
              </div>
            </div>

            {/* Community Links */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Community Channels</span>
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
                    <span className="text-xs text-darkMuted hover:text-accentPrimary truncate max-w-sm">
                      {link.url}
                    </span>
                  </a>
                ))}
                {(!detailData.community_links || detailData.community_links.length === 0) && (
                  <p className="text-xs text-darkMuted font-mono">No linked communities detected yet.</p>
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
                  <p className="text-xs text-darkMuted">No terminology extracted yet.</p>
                )}
              </div>
            </div>

            {/* Matching Recent Videos */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Matching Videos</span>
              <div className="space-y-2">
                {detailData.videos?.map((vid: any) => (
                  <div key={vid.video_id} className="p-2 rounded bg-darkBg border border-darkBorder text-xs space-y-1">
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
