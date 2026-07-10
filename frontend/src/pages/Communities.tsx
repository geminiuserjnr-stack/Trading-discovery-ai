import React from 'react';
import { Share2, ExternalLink } from 'lucide-react';
import { StatusBadge } from '../components/UI';

export const Communities: React.FC = () => {
  const seededCommunities = [
    { name: "Trader XYZ Elite Discord", channel: "Trader XYZ Deutschland", platform: "Discord", url: "https://discord.gg/traderxyz", score: 98, active: true },
    { name: "Börsen Elite Telegram Group", channel: "Börsen Elite", platform: "Telegram", url: "https://t.me/boersenelite", score: 85, active: true },
    { name: "Scalping DE Masterclass Skool", channel: "Scalping DE", platform: "Skool", url: "https://skool.com/scalpingde", score: 92, active: false },
    { name: "Crypto Insider Signal Channel", channel: "Crypto Insider DE", platform: "Telegram", url: "https://t.me/cryptoinsider", score: 89, active: true },
  ];

  return (
    <div className="space-y-6 select-none">
      <div className="flex items-center justify-between border-b border-darkBorder pb-4">
        <div>
          <h1 className="text-lg font-bold uppercase font-mono tracking-widest text-accentPrimary">
            DISCOVERED TRADING COMMUNITIES
          </h1>
          <p className="text-xs text-darkMuted mt-0.5">
            Visualize matched external community platforms, websites, and Skool classrooms.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {seededCommunities.map((c, i) => (
          <div key={i} className="p-4 bg-darkCard border border-darkBorder rounded space-y-3 shadow-subtle flex flex-col justify-between">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-mono tracking-wider text-accentPrimary flex items-center gap-1.5">
                  <Share2 size={12} /> {c.platform}
                </span>
                <h3 className="text-sm font-bold text-darkText font-mono uppercase tracking-wide">
                  {c.name}
                </h3>
                <p className="text-xs text-darkMuted">
                  Associated channel: <span className="text-darkText font-semibold">{c.channel}</span>
                </p>
              </div>
              <StatusBadge status={c.active ? "MONITORED" : "DISCOVERED"} type={c.active ? "success" : "neutral"} />
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-darkBorder/40 flex-shrink-0">
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] font-mono text-darkMuted">INTELLIGENCE SCORE</span>
                <span className="text-xs font-bold font-mono text-accentSuccess">{c.score} / 100</span>
              </div>
              <a
                href={c.url}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-mono font-bold text-accentPrimary hover:underline flex items-center gap-1"
              >
                Inspect Link <ExternalLink size={12} />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
