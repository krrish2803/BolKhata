import React from 'react';
import { motion } from 'framer-motion';
import { copy } from '../content/copy';
import { Clock, HelpCircle, Keyboard, BookX } from 'lucide-react';

const icons = [Clock, HelpCircle, Keyboard];

export const Problem: React.FC = () => {
  return (
    <section id="problem" className="py-20 md:py-28 bg-cream border-b border-navy/10 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-3xl space-y-3">
          <span className="text-xs font-bold tracking-wider uppercase text-khataRed">
            {copy.problem.sectionTag}
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold font-display text-navy tracking-tight">
            {copy.problem.title}
          </h2>
        </div>

        {/* 3 Problem Points Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 mt-12">
          {copy.problem.points.map((pt, idx) => {
            const Icon = icons[idx] || BookX;
            return (
              <motion.div
                key={pt.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ duration: 0.5, delay: idx * 0.15 }}
                className="p-6 sm:p-8 rounded-2xl bg-cream-paper border-2 border-navy/10 hover:border-navy/30 transition-all shadow-paper group"
              >
                <div className="w-12 h-12 rounded-xl bg-khataRed/10 border border-khataRed/20 flex items-center justify-center text-khataRed mb-6 group-hover:scale-110 transition-transform">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold font-display text-navy mb-3">
                  {pt.title}
                </h3>
                <p className="text-sm text-navy/75 leading-relaxed">
                  {pt.description}
                </p>
              </motion.div>
            );
          })}
        </div>

        {/* Bottom Kicker Banner */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-12 p-6 sm:p-8 rounded-2xl bg-navy text-cream flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-paper-lg"
        >
          <div className="space-y-1 max-w-2xl">
            <p className="text-lg sm:text-xl font-bold font-display text-turmeric">
              "{copy.problem.kicker}"
            </p>
            <p className="text-xs sm:text-sm text-cream/70">
              A busy storefront leaves no spare hands. Voice is the only interface fast enough for peak hours.
            </p>
          </div>
          <div className="px-4 py-2.5 rounded-xl bg-navy-light border border-cream/15 text-xs text-cream/80 font-mono flex-shrink-0">
            {copy.problem.statPlaceholder}
          </div>
        </motion.div>

      </div>
    </section>
  );
};
