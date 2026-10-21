import React from 'react';
import { copy } from '../content/copy';
import { Mic, Heart } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-navy-900 text-cream/70 py-16 border-t border-navy/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8 pb-12 border-b border-cream/10">
          
          {/* Brand Info */}
          <div className="space-y-3 max-w-sm">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-navy flex items-center justify-center text-turmeric border border-cream/15">
                <Mic className="w-5 h-5 text-turmeric" />
              </div>
              <span className="font-display font-extrabold text-2xl text-cream tracking-tight">
                {copy.footer.brand}
              </span>
            </div>
            <p className="text-sm text-cream/60 leading-relaxed">
              {copy.footer.tagline}
            </p>
          </div>

          {/* Quick Links */}
          <div className="flex flex-wrap items-center gap-6 text-sm font-medium">
            {copy.navbar.links.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-cream/70 hover:text-turmeric transition-colors"
              >
                {link.label}
              </a>
            ))}
            <a
              href="/auth"
              className="text-turmeric font-bold hover:underline underline-offset-4"
            >
              Demo App
            </a>
          </div>

        </div>

        {/* Bottom Bar with Wispr Challenge Line */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-cream/50">
          <div className="flex items-center gap-1.5">
            <span>{copy.footer.copyright}</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-navy border border-cream/10 text-cream/80 font-medium">
            <Heart className="w-3.5 h-3.5 text-khataRed fill-khataRed" />
            <span>{copy.footer.challengeNote}</span>
          </div>
        </div>

      </div>
    </footer>
  );
};
