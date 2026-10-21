import React from 'react';
import { motion } from 'framer-motion';
import { copy } from '../content/copy';
import { Mic, ArrowRight, CheckCircle2, User, ShoppingBag, Receipt, AlertCircle } from 'lucide-react';

export const Solution: React.FC = () => {
  return (
    <section id="solution" className="py-20 md:py-28 bg-cream-paper border-b border-navy/10 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-16">
          <span className="text-xs font-bold tracking-wider uppercase text-turmeric-hover bg-turmeric/20 px-3 py-1 rounded-full border border-turmeric/40">
            {copy.solution.sectionTag}
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold font-display text-navy tracking-tight">
            {copy.solution.title}
          </h2>
          <p className="text-base sm:text-lg text-navy/75 leading-relaxed">
            {copy.solution.description}
          </p>
        </div>

        {/* Side-by-side spoken vs structured transformation */}
        <div className="grid grid-cols-1 lg:grid-cols-11 gap-6 items-center">
          
          {/* Left: Spoken Natural Hinglish Audio Card */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-5 p-6 sm:p-8 rounded-2xl bg-cream border-2 border-navy/15 shadow-paper space-y-6 relative overflow-hidden"
          >
            <div className="flex items-center justify-between border-b border-navy/10 pb-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-turmeric animate-ping" />
                <span className="text-xs font-bold uppercase tracking-wider text-navy/60">
                  Spoken Dictation
                </span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-turmeric text-navy font-bold text-xs">
                <Mic className="w-3.5 h-3.5" />
                <span>Audio Stream</span>
              </div>
            </div>

            <div className="space-y-4">
              <div className="text-lg sm:text-xl font-medium text-navy leading-snug italic font-display">
                {copy.solution.spokenSentence}
              </div>

              {/* Audio Waveform visualization */}
              <div className="h-10 flex items-center justify-between gap-1 px-4 py-2 bg-navy/5 rounded-xl">
                {[40, 70, 30, 90, 60, 100, 45, 80, 50, 95, 60, 35, 75, 50, 85, 40].map((h, i) => (
                  <motion.div
                    key={i}
                    className="w-1.5 bg-turmeric rounded-full"
                    animate={{ height: [`${h * 0.4}%`, `${h}%`, `${h * 0.3}%`] }}
                    transition={{
                      repeat: Infinity,
                      duration: 1.2,
                      delay: i * 0.08,
                      ease: 'easeInOut',
                    }}
                  />
                ))}
              </div>
            </div>

            <div className="text-xs text-navy/60 flex items-center gap-2">
              <span className="font-semibold text-navy">Shop Owner speech:</span>
              <span>Zero special syntax, just normal counter talk.</span>
            </div>
          </motion.div>

          {/* Center Animated Arrow Connector */}
          <div className="lg:col-span-1 flex justify-center py-2 lg:py-0">
            <div className="w-12 h-12 rounded-full bg-navy text-turmeric flex items-center justify-center shadow-md animate-pulse">
              <ArrowRight className="w-6 h-6 rotate-90 lg:rotate-0" />
            </div>
          </div>

          {/* Right: Structured Digital Ledger Entry Card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-5 p-6 sm:p-8 rounded-2xl bg-navy text-cream border-2 border-navy shadow-paper-lg space-y-6"
          >
            <div className="flex items-center justify-between border-b border-cream/15 pb-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-khataGreen" />
                <span className="text-xs font-bold uppercase tracking-wider text-cream/70">
                  Digital Ledger Entry
                </span>
              </div>
              <span className="text-xs font-mono text-turmeric">Auto-Categorized</span>
            </div>

            {/* Structured Table */}
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-cream/10 text-sm">
                <div className="flex items-center gap-2 text-cream/70">
                  <User className="w-4 h-4 text-turmeric" />
                  <span>Customer:</span>
                </div>
                <span className="font-bold text-cream font-display">
                  {copy.solution.parsedEntry.customer}
                </span>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-cream/10 text-sm">
                <div className="flex items-center gap-2 text-cream/70">
                  <ShoppingBag className="w-4 h-4 text-turmeric" />
                  <span>Items:</span>
                </div>
                <span className="font-medium text-cream">
                  {copy.solution.parsedEntry.items}
                </span>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-cream/10 text-sm">
                <div className="flex items-center gap-2 text-cream/70">
                  <Receipt className="w-4 h-4 text-turmeric" />
                  <span>Total Bill:</span>
                </div>
                <span className="font-bold text-turmeric text-base font-display">
                  {copy.solution.parsedEntry.total}
                </span>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-cream/10 text-sm">
                <span className="text-cream/70">Paid (Jama):</span>
                <span className="font-bold text-khataGreen px-2 py-0.5 rounded bg-khataGreen/20">
                  {copy.solution.parsedEntry.paid}
                </span>
              </div>

              <div className="flex items-center justify-between py-2 text-sm">
                <span className="text-cream/70">Due (Udhaar):</span>
                <span className="font-bold text-khataRed px-2 py-0.5 rounded bg-khataRed/20">
                  {copy.solution.parsedEntry.due}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-navy-light flex items-center justify-between text-xs text-cream/80">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-khataGreen" />
                {copy.solution.parsedEntry.status}
              </span>
              <span className="text-turmeric font-semibold">WhatsApp Ready ✓</span>
            </div>
          </motion.div>

        </div>

      </div>
    </section>
  );
};
