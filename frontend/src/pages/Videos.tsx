import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { PlaySquare, RefreshCw, ShieldCheck } from 'lucide-react';
import { Button, StatusBadge, SearchBox, Drawer, LoadingSkeleton, ErrorState, EmptyState } from '../components/UI';
import { API_BASE_URL } from '../config';

export const Videos: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [processedOnly, setProcessedOnly] = useState(false);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);

  // Auto-open video if ID provided in query params
  const urlVideoId = searchParams.get('id');
  useEffect(() => {
    if (urlVideoId) {
      setSelectedVideoId(urlVideoId);
    }
  }, [urlVideoId]);

  // Fetch Videos
  const { data: videos, isLoading, error, refetch } = useQuery<any[]>({
    queryKey: ['videos', processedOnly],
    queryFn: async () => {
      const url = `${API_BASE_URL}/videos?limit=100&processed_only=${processedOnly}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to retrieve discovered videos');
      return res.json();
    }
  });

  // Fetch Video Detail
  const { data: detailData, isLoading: isDetailLoading } = useQuery<any>({
    queryKey: ['video-detail', selectedVideoId],
    queryFn: async () => {
      if (!selectedVideoId) return null;
      const res = await fetch(`${API_BASE_URL}/videos/${selectedVideoId}`);
      if (!res.ok) throw new Error('Failed to retrieve video detailed profile');
      return res.json();
    },
    enabled: !!selectedVideoId
  });

  // Filter videos locally
  const filteredVideos = videos?.filter(vid =>
    vid.title.toLowerCase().includes(search.toLowerCase()) ||
    vid.video_id.toLowerCase().includes(search.toLowerCase()) ||
    vid.channel_id.toLowerCase().includes(search.toLowerCase())
  ) || [];

  const handleOpenDetail = (videoId: string) => {
    setSelectedVideoId(videoId);
    setSearchParams({ id: videoId });
  };

  const handleCloseDetail = () => {
    setSelectedVideoId(null);
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
            CRAWLED YOUTUBE VIDEOS
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Browse and inspect video titles, transcript downloads, and extracted terminology logs.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant={processedOnly ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setProcessedOnly(!processedOnly)}
          >
            Processed Only
          </Button>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw size={12} className="mr-1" /> Reload
          </Button>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex items-center justify-between bg-darkCard border border-darkBorder rounded p-3 flex-shrink-0">
        <SearchBox value={search} onChange={setSearch} placeholder="Search title, video ID, channel ID..." />
        <div className="text-xs text-darkMuted font-mono">
          Showing <span className="text-accentPrimary">{filteredVideos.length}</span> of {videos?.length || 0} videos
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 bg-darkCard border border-darkBorder rounded overflow-hidden shadow-subtle flex flex-col">
        {isLoading ? (
          <div className="p-8"><LoadingSkeleton /></div>
        ) : filteredVideos.length === 0 ? (
          <EmptyState title="No Videos Discovered" message="Run queries or trigger crawler runs to gather videos." />
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-darkBg border-b border-darkBorder sticky top-0 z-10">
                <tr className="text-[10px] uppercase font-mono tracking-wider text-darkMuted h-10">
                  <th className="pl-4 py-2 font-semibold">Video Title</th>
                  <th className="py-2 font-semibold">Channel ID</th>
                  <th className="py-2 font-semibold">Published Date</th>
                  <th className="py-2 font-semibold">Views</th>
                  <th className="py-2 font-semibold">Transcript</th>
                  <th className="py-2 font-semibold">Language</th>
                  <th className="py-2 font-semibold">Processed</th>
                  <th className="pr-4 py-2 text-right font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder">
                {filteredVideos.map((vid) => (
                  <tr
                    key={vid.video_id}
                    onClick={() => handleOpenDetail(vid.video_id)}
                    className="h-10 text-xs text-darkText hover:bg-darkBg/60 cursor-pointer transition-colors border-b border-darkBorder"
                  >
                    <td className="pl-4 py-1.5 font-semibold text-darkText flex items-center gap-2 max-w-[280px]">
                      <PlaySquare size={14} className="text-accentPrimary" />
                      <span className="truncate">{vid.title}</span>
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkMuted truncate max-w-[150px]">
                      {vid.channel_id}
                    </td>
                    <td className="py-1.5 font-mono text-[10px] text-darkMuted">
                      {new Date(vid.published_at).toLocaleDateString()}
                    </td>
                    <td className="py-1.5 font-mono text-xs">
                      {vid.view_count ? vid.view_count.toLocaleString() : '0'}
                    </td>
                    <td className="py-1.5">
                      <StatusBadge
                        status={vid.transcript_available ? 'AVAILABLE' : 'MISSING'}
                        type={vid.transcript_available ? 'success' : 'neutral'}
                      />
                    </td>
                    <td className="py-1.5 uppercase font-mono text-[10px] text-accentPrimary">
                      {vid.language || 'de'}
                    </td>
                    <td className="py-1.5">
                      <StatusBadge
                        status={vid.processed ? 'PROCESSED' : 'PENDING'}
                        type={vid.processed ? 'success' : 'warning'}
                      />
                    </td>
                    <td className="pr-4 py-1.5 text-right">
                      <StatusBadge status="OK" type="success" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Video Detail Profile Drawer */}
      <Drawer
        isOpen={!!selectedVideoId}
        onClose={handleCloseDetail}
        title="VIDEO_DETAIL"
      >
        {isDetailLoading ? (
          <LoadingSkeleton />
        ) : detailData ? (
          <div className="space-y-6">
            {/* Header info */}
            <div className="p-4 rounded bg-darkBg border border-darkBorder space-y-1.5">
              <span className="text-[9px] font-mono tracking-widest text-accentPrimary block uppercase">VIDEO METADATA</span>
              <h2 className="text-sm font-bold text-darkText font-mono uppercase tracking-wide leading-snug">
                {detailData.video?.title}
              </h2>
              <div className="flex flex-wrap items-center gap-4 text-[10px] text-darkMuted font-mono pt-1">
                <span>Views: {detailData.video?.view_count?.toLocaleString()}</span>
                <span>Duration: {detailData.video?.duration ? `${Math.round(detailData.video.duration / 60)} mins` : 'N/A'}</span>
                <span>Date: {detailData.video?.published_at ? new Date(detailData.video.published_at).toLocaleDateString() : ''}</span>
              </div>
            </div>

            {/* Channels & Source Information */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-darkBg border border-darkBorder rounded space-y-0.5">
                <span className="text-[9px] font-mono text-darkMuted uppercase">Channel</span>
                <span className="text-xs font-bold font-mono text-darkText truncate block">
                  {detailData.channel_name}
                </span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded space-y-0.5">
                <span className="text-[9px] font-mono text-darkMuted uppercase">Discovery Source</span>
                <span className="text-xs font-bold font-mono text-accentPrimary truncate block">
                  {detailData.discovery_source || 'Seed'}
                </span>
              </div>
            </div>

            {/* Processing History steps */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Processing History</span>
              <div className="space-y-2 bg-darkBg/30 border border-darkBorder/40 p-3 rounded">
                {detailData.processing_history?.map((step: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between text-xs font-mono">
                    <span className="text-darkMuted">{step.step}:</span>
                    <span className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${step.status === 'completed' ? 'bg-accentSuccess' : 'bg-accentDanger'}`} />
                      <span className={step.status === 'completed' ? 'text-accentSuccess' : 'text-accentDanger'}>
                        {step.status}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Language Evaluation Details */}
            <div className="p-3 bg-darkBg border border-darkBorder rounded flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="text-accentSuccess" size={16} />
                <span className="text-xs font-mono text-darkMuted uppercase">Language Confidence:</span>
              </div>
              <span className="text-xs font-mono font-bold text-accentSuccess">
                {detailData.language_confidence ? `${Math.round(detailData.language_confidence * 100)}% de` : '100% de'}
              </span>
            </div>

            {/* Extracted phrases in this Video */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Extracted Terminology</span>
              <div className="flex flex-wrap gap-1.5">
                {detailData.phrases?.map((ph: any) => (
                  <span
                    key={ph.phrase}
                    className="text-xs font-mono px-2 py-1 rounded bg-darkBg border border-darkBorder flex items-center gap-2"
                  >
                    <span className="text-darkText font-medium">{ph.phrase}</span>
                    <span className="text-[9px] px-1 rounded bg-darkCard text-accentPrimary border border-darkBorder/40">
                      {ph.count}x
                    </span>
                  </span>
                ))}
                {(!detailData.phrases || detailData.phrases.length === 0) && (
                  <p className="text-xs text-darkMuted font-mono">No phrases extracted in this video.</p>
                )}
              </div>
            </div>

            {/* Video Transcript Panel */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Full Cached Transcript</span>
              <div className="p-4 rounded bg-darkBg border border-darkBorder text-xs text-darkText leading-relaxed font-mono max-h-60 overflow-y-auto whitespace-pre-wrap">
                {detailData.transcript || 'Transcript not available.'}
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
