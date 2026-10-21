import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { copy } from '../content/copy';
import { Mic, ArrowRight, Play, Volume2, Sparkles, Loader2 } from 'lucide-react';
import { InteractiveLedgerHeroCard } from './InteractiveLedgerHeroCard';
import { useAuth } from '../context/AuthContext';

export const Hero: React.FC = () => {
  const navigate = useNavigate();
  const { startDemoSession } = useAuth();
  const [demoLoading, setDemoLoading] = useState(false);

  const handleDemoClick = async () => {
    try {
      setDemoLoading(true);
      const res = await startDemoSession();
      if (res.success) {
        navigate('/app');
      } else {
        navigate('/auth');
      }
    } catch {
      navigate('/auth');
    } finally {
      setDemoLoading(false);
    }
  };
  return (
    <section className="relative overflow-hidden pt-8 pb-16 md:pt-16 md:pb-24 border-b border-navy/10">
      {/* Subtle traditional ledger red margin line on left */}
      <div className="absolute left-6 md:left-16 top-0 bottom-0 w-[1px] bg-khataRed/20 pointer-events-none hidden sm:block" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          
          {/* Left Text Column */}
          <div className="lg:col-span-6 space-y-6 text-left">
            {/* Indian Counter Badge */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-turmeric/20 border border-turmeric/40 text-navy font-semibold text-xs tracking-wide"
            >
              <Sparkles className="w-3.5 h-3.5 text-navy fill-turmeric" />
              <span>{copy.hero.badge}</span>
            </motion.div>

            {/* Main Headline */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-5xl sm:text-6xl lg:text-7xl font-extrabold font-display text-navy tracking-tight leading-[1.08]"
            >
              Bolo. <span className="underline decoration-turmeric decoration-wavy decoration-4">Likho mat.</span>
            </motion.h1>

            {/* Subheadline */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-lg sm:text-xl text-navy/80 max-w-2xl font-normal leading-relaxed"
            >
              {copy.hero.subheadline}
            </motion.p>

            {/* Primary & Secondary CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 pt-2"
            >
              <button
                type="button"
                onClick={handleDemoClick}
                disabled={demoLoading}
                className="inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-xl bg-turmeric hover:bg-turmeric-hover text-navy font-extrabold text-base shadow-paper-lg hover:shadow-turmeric-glow transition-all active:scale-[0.98] border-2 border-navy/20"
              >
                {demoLoading ? (
                  <Loader2 className="w-5 h-5 text-navy animate-spin" />
                ) : (
                  <Sparkles className="w-5 h-5 text-navy fill-navy/30" />
                )}
                <span>{demoLoading ? 'Starting Demo...' : 'Try the demo (1-Click)'}</span>
                <ArrowRight className="w-4 h-4 text-navy" />
              </button>

              <Link
                to="/auth"
                className="inline-flex items-center justify-center gap-2 px-6 py-4 rounded-xl bg-navy hover:bg-navy-light text-turmeric font-bold text-base shadow-paper hover:shadow-turmeric-glow transition-all active:scale-[0.98]"
              >
                <Mic className="w-4 h-4 text-turmeric" />
                <span>Sign In / Open Khata</span>
              </Link>
            </motion.div>

            {/* Spoken Hinglish Example Bar */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="pt-2"
            >
              <div className="p-4 rounded-xl bg-cream-paper border-2 border-turmeric/40 shadow-sm flex items-start sm:items-center gap-3">
                <div className="p-2 rounded-lg bg-turmeric text-navy mt-0.5 sm:mt-0 flex-shrink-0">
                  <Volume2 className="w-4 h-4" />
                </div>
                <div className="text-xs sm:text-sm text-navy/90 font-medium italic">
                  {copy.hero.dictationExample}
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Useful Interactive Product Column */}
          <div className="lg:col-span-6 relative flex items-center justify-center">
            {/* Background warm aura */}
            <div className="absolute w-72 h-72 sm:w-96 sm:h-96 rounded-full bg-turmeric/20 blur-3xl -z-10 pointer-events-none" />
            <InteractiveLedgerHeroCard />
          </div>
        </div>
      </div>
    </section>
  );
};
