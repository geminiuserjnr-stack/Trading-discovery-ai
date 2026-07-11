import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Hash, RefreshCw, Layers, TrendingUp, ArrowRight } from 'lucide-react';
import { Button, SearchBox, Drawer, LoadingSkeleton, ErrorState, EmptyState } from '../components/UI';
import { API_BASE_URL } from '../config';

export const Phrases: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [minQuality, setMinQuality] = useState(0.0);
  const [selectedPhrase, setSelectedPhrase] = useState<string | null>(null);

  // Auto-open phrase detail if provided in URL params
  const urlPhrase = searchParams.get('id');
  useEffect(() => {
    if (urlPhrase) {
      setSelectedPhrase(urlPhrase);
    }
  }, [urlPhrase]);

  // Fetch Phrases List
  const { data: phrases, isLoading, error, refetch } = useQuery<any[]>({
    queryKey: ['phrases', minQuality],
    queryFn: async () => {
      const url = `${API_BASE_URL}/phrases?limit=100&min_quality=${minQuality}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to retrieve extracted terminology phrases');
      return res.json();
    }
  });

  // Fetch Phrase Detail
  const { data: detailData, isLoading: isDetailLoading } = useQuery<any>({
    queryKey: ['phrase-detail', selectedPhrase],
    queryFn: async () => {
      if (!selectedPhrase) return null;
      const res = await fetch(`${API_BASE_URL}/phrases/${encodeURIComponent(selectedPhrase)}`);
      if (!res.ok) throw new Error('Failed to retrieve phrase specific details');
      return res.json();
    },
    enabled: !!selectedPhrase
  });

  // Filter phrases locally
  const filteredPhrases = phrases?.filter(p =>
    p.phrase.toLowerCase().includes(search.toLowerCase())
  ) || [];

  const handleOpenDetail = (phraseName: string) => {
    setSelectedPhrase(phraseName);
    setSearchParams({ id: phraseName });
  };

  const handleCloseDetail = () => {
    setSelectedPhrase(null);
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
            EXTRACTED GERMAN TERMINOLOGY
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Phrase Explorer: Browse unique German-speaking trading terms parsed by NLP.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={minQuality}
            onChange={(e) => setMinQuality(parseFloat(e.target.value))}
            className="h-8 px-2.5 rounded bg-darkCard border border-darkBorder text-xs text-darkText focus:outline-none focus:border-accentPrimary transition-colors"
          >
            <option value={0.0}>Min Quality: All</option>
            <option value={5.0}>Min Quality: 5.0+</option>
            <option value={8.0}>Min Quality: 8.0+</option>
            <option value={9.0}>Min Quality: 9.0+</option>
          </select>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw size={12} className="mr-1" /> Reload
          </Button>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex items-center justify-between bg-darkCard border border-darkBorder rounded p-3 flex-shrink-0">
        <SearchBox value={search} onChange={setSearch} placeholder="Search phrase text..." />
        <div className="text-xs text-darkMuted font-mono">
          Showing <span className="text-accentPrimary">{filteredPhrases.length}</span> of {phrases?.length || 0} phrases
        </div>
      </div>

      {/* Main Content Table */}
      <div className="flex-1 bg-darkCard border border-darkBorder rounded overflow-hidden shadow-subtle flex flex-col">
        {isLoading ? (
          <div className="p-8"><LoadingSkeleton /></div>
        ) : filteredPhrases.length === 0 ? (
          <EmptyState title="No Terminology Extracted" message="Ensure transcripts are collected and processed by NLP." />
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-darkBg border-b border-darkBorder sticky top-0 z-10">
                <tr className="text-[10px] uppercase font-mono tracking-wider text-darkMuted h-10">
                  <th className="pl-4 py-2 font-semibold">Phrase</th>
                  <th className="py-2 font-semibold">Frequency</th>
                  <th className="py-2 font-semibold">Unique Channels</th>
                  <th className="py-2 font-semibold">Unique Videos</th>
                  <th className="py-2 font-semibold">Quality Score</th>
                  <th className="py-2 font-semibold">Growth Trend</th>
                  <th className="pr-4 py-2 text-right font-semibold">Language</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder">
                {filteredPhrases.map((p) => (
                  <tr
                    key={p.phrase}
                    onClick={() => handleOpenDetail(p.phrase)}
                    className="h-10 text-xs text-darkText hover:bg-darkBg/60 cursor-pointer transition-colors border-b border-darkBorder"
                  >
                    <td className="pl-4 py-1.5 font-bold font-mono text-darkText flex items-center gap-2">
                      <Hash size={13} className="text-accentWarning" />
                      <span>{p.phrase}</span>
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkText">{p.frequency}</td>
                    <td className="py-1.5 font-mono text-xs text-darkMuted flex items-center gap-1">
                      <Layers size={11} /> {p.unique_channels}
                    </td>
                    <td className="py-1.5 font-mono text-xs text-darkMuted">
                      {p.unique_videos}
                    </td>
                    <td className="py-1.5">
                      <span className="font-mono text-xs font-bold text-accentPrimary">
                        {p.quality_score?.toFixed(1) || '0.0'}
                      </span>
                    </td>
                    <td className="py-1.5">
                      <span className="text-[10px] text-accentSuccess font-mono font-semibold flex items-center gap-0.5">
                        <TrendingUp size={10} /> +12.4%
                      </span>
                    </td>
                    <td className="pr-4 py-1.5 text-right uppercase font-mono text-[10px] text-darkMuted">
                      {p.language || 'de'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Phrase Detail Drawer */}
      <Drawer
        isOpen={!!selectedPhrase}
        onClose={handleCloseDetail}
        title="PHRASE_INTELLIGENCE"
      >
        {isDetailLoading ? (
          <LoadingSkeleton />
        ) : detailData ? (
          <div className="space-y-6">
            {/* Phrase Heading */}
            <div className="p-4 rounded bg-darkBg border border-darkBorder space-y-1">
              <span className="text-[9px] font-mono tracking-widest text-accentWarning block uppercase">ACTIVE TERMINOLOGY</span>
              <h2 className="text-sm font-bold text-darkText font-mono uppercase tracking-wider">
                {detailData.phrase?.phrase}
              </h2>
            </div>

            {/* Quality Score & Frequency stats */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-darkBg border border-darkBorder rounded text-center">
                <span className="text-[9px] font-mono text-darkMuted block">QUALITY SCORE</span>
                <span className="text-base font-bold font-mono text-accentPrimary">
                  {detailData.phrase?.quality_score?.toFixed(1) || '0.0'}
                </span>
              </div>
              <div className="p-3 bg-darkBg border border-darkBorder rounded text-center">
                <span className="text-[9px] font-mono text-darkMuted block">TOTAL FREQUENCY</span>
                <span className="text-base font-bold font-mono text-accentWarning">
                  {detailData.phrase?.frequency || 1}
                </span>
              </div>
            </div>

            {/* Frequency trend graph representation */}
            <div className="space-y-1.5">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Frequency Growth Trend</span>
              <div className="p-3 bg-darkBg border border-darkBorder rounded flex items-end justify-between h-20 px-6">
                {detailData.frequency_trend?.map((t: any) => (
                  <div key={t.day} className="flex flex-col items-center gap-1">
                    <div
                      className="w-2 bg-accentWarning/85 rounded-t"
                      style={{ height: `${(t.frequency / Math.max(...detailData.frequency_trend.map((x: any) => x.frequency))) * 45}px` }}
                    />
                    <span className="text-[9px] font-mono text-darkMuted">{t.day}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Related phrases relationships */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Related Co-occurring Phrases</span>
              <div className="space-y-1.5">
                {detailData.related_phrases?.map((rel: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded bg-darkBg border border-darkBorder/60 text-xs"
                  >
                    <span className="font-mono text-darkText">{rel.phrase}</span>
                    <span className="text-[9px] uppercase font-mono text-accentPrimary px-1.5 py-0.5 rounded bg-darkCard border border-darkBorder">
                      strength: {Math.round(rel.strength * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Generated search queries linked to this phrase */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Generated Search Queries</span>
              <div className="space-y-1.5">
                {detailData.generated_queries?.map((q: string, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 p-2 rounded bg-darkBg border border-darkBorder text-xs font-mono text-darkText"
                  >
                    <ArrowRight size={10} className="text-accentPrimary" />
                    <span>{q}</span>
                  </div>
                ))}
                {(!detailData.generated_queries || detailData.generated_queries.length === 0) && (
                  <p className="text-xs text-darkMuted font-mono">No queries generated for this phrase yet.</p>
                )}
              </div>
            </div>

            {/* Channels using it */}
            <div className="space-y-2">
              <span className="text-[9px] font-mono tracking-widest text-darkMuted block uppercase">Channels Using Terminology</span>
              <div className="space-y-1.5">
                {detailData.channels?.map((ch: any) => (
                  <div
                    key={ch.channel_id}
                    className="flex items-center justify-between p-2 rounded bg-darkBg border border-darkBorder text-xs"
                  >
                    <span className="text-darkText font-semibold">{ch.channel_name}</span>
                    <span className="text-[9px] font-mono text-darkMuted">{ch.channel_id}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Videos containing it */}
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
