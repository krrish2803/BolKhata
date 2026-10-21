import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { copy } from '../content/copy';
import { Languages, ShieldCheck, Scale, Boxes, MessageSquareShare, HelpCircle } from 'lucide-react';

const iconMap: Record<string, React.FC<{ className?: string }>> = {
  hinglish: Languages,
  confirm: ShieldCheck,
  udhaar: Scale,
  stock: Boxes,
  receipts: MessageSquareShare,
  ask: HelpCircle,
};

export const Features: React.FC = () => {
  return (
    <section id="features" className="py-20 md:py-28 bg-cream border-b border-navy/10 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-16">
          <span className="text-xs font-bold tracking-wider uppercase text-turmeric-hover bg-turmeric/20 px-3 py-1 rounded-full border border-turmeric/40">
            {copy.features.sectionTag}
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold font-display text-navy tracking-tight">
            {copy.features.title}
          </h2>
          <p className="text-base sm:text-lg text-navy/75 leading-relaxed">
            {copy.features.subtitle}
          </p>
        </div>

        {/* 6 Feature Cards with subtle 3D hover tilt */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
          {copy.features.cards.map((card, idx) => {
            const Icon = iconMap[card.id] || Languages;
            return <FeatureCard key={card.id} card={card} idx={idx} Icon={Icon} />;
          })}
        </div>

      </div>
    </section>
  );
};

interface CardProps {
  card: typeof copy.features.cards[0];
  idx: number;
  Icon: React.FC<{ className?: string }>;
}

const FeatureCard: React.FC<CardProps> = ({ card, idx, Icon }) => {
  const [rotate, setRotate] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    setRotate({
      x: -y * 0.04,
      y: x * 0.04,
    });
  };

  const handleMouseLeave = () => {
    setRotate({ x: 0, y: 0 });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 25 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5, delay: idx * 0.1 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: `perspective(800px) rotateX(${rotate.x}deg) rotateY(${rotate.y}deg)`,
        transition: 'transform 0.15s ease-out',
      }}
      className="p-8 rounded-2xl bg-cream-paper border-2 border-navy/10 hover:border-turmeric/80 shadow-paper hover:shadow-paper-lg flex flex-col justify-between group cursor-default"
    >
      <div>
        <div className="flex items-center justify-between mb-6">
          <div className="w-12 h-12 rounded-xl bg-navy text-turmeric flex items-center justify-center shadow-md group-hover:scale-110 group-hover:bg-turmeric group-hover:text-navy transition-all duration-300">
            <Icon className="w-6 h-6" />
          </div>
          <span className="text-xs font-mono font-bold text-navy/40 group-hover:text-navy/70">
            0{idx + 1}
          </span>
        </div>

        <h3 className="text-xl font-bold font-display text-navy mb-1 group-hover:text-navy transition-colors">
          {card.title}
        </h3>
        <p className="text-xs font-semibold text-turmeric-hover uppercase tracking-wider mb-3">
          {card.tagline}
        </p>

        <p className="text-sm text-navy/75 leading-relaxed">
          {card.description}
        </p>
      </div>

      <div className="pt-6 mt-6 border-t border-navy/5 flex items-center justify-between text-xs font-medium text-navy/60">
        <span className="group-hover:text-navy font-semibold transition-colors">Voice native</span>
        <span className="text-khataGreen">Always active</span>
      </div>
    </motion.div>
  );
};
