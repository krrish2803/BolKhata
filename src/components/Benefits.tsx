import React from 'react';
import { motion } from 'framer-motion';
import { copy } from '../content/copy';
import { Zap, ShieldAlert, Layers, Smartphone, Store } from 'lucide-react';

const icons = [Zap, ShieldAlert, Layers, Smartphone];

export const Benefits: React.FC = () => {
  return (
    <section className="py-20 md:py-28 bg-cream border-b border-navy/10 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-16">
          <span className="text-xs font-bold tracking-wider uppercase text-khataGreen bg-khataGreen/15 px-3 py-1 rounded-full border border-khataGreen/30">
            {copy.benefits.sectionTag}
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold font-display text-navy tracking-tight">
            {copy.benefits.title}
          </h2>
          <p className="text-base sm:text-lg text-navy/75 leading-relaxed">
            {copy.benefits.subtitle}
          </p>
        </div>

        {/* 4 Benefit Blocks */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
          {copy.benefits.blocks.map((b, idx) => {
            const Icon = icons[idx] || Zap;
            return (
              <motion.div
                key={b.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ duration: 0.5, delay: idx * 0.12 }}
                className="p-8 rounded-2xl bg-cream-paper border-2 border-navy/10 hover:border-navy/30 transition-all shadow-paper group"
              >
                <div className="w-12 h-12 rounded-xl bg-navy text-turmeric flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold font-display text-navy mb-2">
                  {b.title}
                </h3>
                <p className="text-sm sm:text-base text-navy/75 leading-relaxed">
                  {b.description}
                </p>
              </motion.div>
            );
          })}
        </div>

        {/* Shop types callout note */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-12 p-6 sm:p-8 rounded-2xl bg-turmeric/20 border-2 border-turmeric/50 flex items-start sm:items-center gap-4 text-navy"
        >
          <div className="p-3 rounded-xl bg-turmeric text-navy flex-shrink-0">
            <Store className="w-6 h-6" />
          </div>
          <div>
            <span className="font-bold font-display text-base text-navy block mb-0.5">
              Designed for actual physical retail counters:
            </span>
            <p className="text-sm text-navy/85 leading-relaxed">
              {copy.benefits.shopTypesNote}
            </p>
          </div>
        </motion.div>

      </div>
    </section>
  );
};
