import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Percent, Layers, RefreshCw } from 'lucide-react';
import { LoadingSkeleton, ErrorState, EmptyState, Button } from '../components/UI';
import { API_BASE_URL } from '../config';

export const Scoring: React.FC = () => {
  // Fetch actual phrase scores from the backend
  const { data: phrases, isLoading, error, refetch } = useQuery<any[]>({
    queryKey: ['scoring-phrases'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/phrases?limit=50&min_quality=0.0`);
      if (!res.ok) throw new Error('Failed to retrieve terminology phrases for scoring');
      return res.json();
    }
  });

  if (error) {
    return <ErrorState message={(error as Error).message} onRetry={refetch} />;
  }

  // Sort phrases by quality score descending
  const sortedPhrases = phrases ? [...phrases].sort((a, b) => b.quality_score - a.quality_score) : [];

  return (
    <div className="space-y-6 select-none h-full flex flex-col">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-darkBorder pb-4 flex-shrink-0">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary flex items-center gap-2">
            <Percent size={18} /> GERMAN TERMINOLOGY NICHE QUALITY SCORING
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Active evaluation table displaying linguistic weight, frequency metrics, and quality coefficients.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          <RefreshCw size={12} className="mr-1" /> Refresh Scores
        </Button>
      </div>

      {/* Main Content Table */}
      <div className="flex-1 bg-darkCard border border-darkBorder rounded overflow-hidden shadow-subtle flex flex-col">
        {isLoading ? (
          <div className="p-8"><LoadingSkeleton /></div>
        ) : sortedPhrases.length === 0 ? (
          <EmptyState
            title="No Terminology Scored Yet"
            message="Phrases will appear here once transcripts are crawled and analysed by the NLP pipelines."
          />
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-darkBg border-b border-darkBorder sticky top-0 z-10">
                <tr className="text-[10px] uppercase font-mono tracking-wider text-darkMuted h-10">
                  <th className="pl-4 py-2 font-semibold">German Phrase</th>
                  <th className="py-2 font-semibold">Linguistic Weight</th>
                  <th className="py-2 font-semibold">Total Frequency</th>
                  <th className="py-2 font-semibold">Unique Channels</th>
                  <th className="py-2 font-semibold">Unique Videos</th>
                  <th className="pr-4 py-2 text-right font-semibold">Dynamic Quality Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-darkBorder">
                {sortedPhrases.map((p) => {
                  const scoreColor = p.quality_score >= 8.5 ? 'text-accentSuccess' : p.quality_score >= 6.5 ? 'text-accentPrimary' : 'text-accentWarning';
                  return (
                    <tr
                      key={p.phrase}
                      className="h-10 text-xs text-darkText hover:bg-darkBg/60 transition-colors border-b border-darkBorder"
                    >
                      <td className="pl-4 py-1.5 font-bold font-mono text-darkText flex items-center gap-2">
                        <span className="text-darkText">{p.phrase}</span>
                      </td>
                      <td className="py-1.5 font-mono text-xs text-darkMuted">
                        {(p.average_recency || 0.9).toFixed(2)} coeff
                      </td>
                      <td className="py-1.5 font-mono text-xs text-darkText">{p.frequency}</td>
                      <td className="py-1.5 font-mono text-xs text-darkMuted flex items-center gap-1">
                        <Layers size={11} /> {p.unique_channels}
                      </td>
                      <td className="py-1.5 font-mono text-xs text-darkMuted">
                        {p.unique_videos}
                      </td>
                      <td className="pr-4 py-1.5 text-right font-mono font-bold text-sm">
                        <span className={scoreColor}>{p.quality_score?.toFixed(1) || '0.0'} / 10.0</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
