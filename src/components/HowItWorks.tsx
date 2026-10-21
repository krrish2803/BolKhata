import React, { Suspense, useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { copy } from '../content/copy';
import { WebGLErrorBoundary, isWebGLAvailable } from './WebGLErrorBoundary';
import { Mic, CheckCircle2, MessageSquare, ArrowRight, Smartphone, Sparkles } from 'lucide-react';

const StepsScene = React.lazy(() =>
  import('../three/StepsScene').then((mod) => ({ default: mod.StepsScene }))
);

export const HowItWorks: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [canRenderWebGL, setCanRenderWebGL] = useState(true);

  useEffect(() => {
    setCanRenderWebGL(isWebGLAvailable());
  }, []);

  return (
    <section id="how-it-works" className="py-20 md:py-28 bg-cream-paper border-b border-navy/10 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Heading */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-16">
          <span className="text-xs font-bold tracking-wider uppercase text-turmeric-hover bg-turmeric/20 px-3 py-1 rounded-full border border-turmeric/40">
            {copy.howItWorks.sectionTag}
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold font-display text-navy tracking-tight">
            {copy.howItWorks.title}
          </h2>
          <p className="text-base sm:text-lg text-navy/75 leading-relaxed">
            {copy.howItWorks.subtitle}
          </p>
        </div>

        {/* Two-column layout: Sticky 3D scene on left/desktop, scrolling steps on right */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
          
          {/* Left Sticky 3D Viewport */}
          <div className="lg:col-span-6 lg:sticky lg:top-28 z-20">
            <div className="p-4 sm:p-6 rounded-3xl bg-cream border-2 border-navy/15 shadow-paper-lg overflow-hidden relative">
              {/* Step indicator header inside 3D card */}
              <div className="flex items-center justify-between pb-3 border-b border-navy/10">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-turmeric animate-ping" />
                  <span className="text-xs font-bold uppercase tracking-wider text-navy">
                    Interactive 3D Stage
                  </span>
                </div>
                <span className="text-xs font-mono font-bold text-navy/60">
                  Step 0{activeStep + 1} / 05
                </span>
              </div>

              {/* 3D Canvas / Fallback */}
              <div className="w-full h-[380px] sm:h-[440px] md:h-[480px] relative flex items-center justify-center">
                {canRenderWebGL ? (
                  <WebGLErrorBoundary fallback={<StepsFallbackVisual activeStep={activeStep} />}>
                    <Suspense fallback={<StepsLoadingFallback />}>
                      <StepsScene activeStep={activeStep} />
                    </Suspense>
                  </WebGLErrorBoundary>
                ) : (
                  <StepsFallbackVisual activeStep={activeStep} />
                )}
              </div>

              {/* Bottom active step indicator pills */}
              <div className="pt-3 border-t border-navy/10 flex items-center justify-between">
                <div className="flex gap-1.5">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <button
                      key={i}
                      onClick={() => setActiveStep(i)}
                      className={`h-2 rounded-full transition-all ${
                        activeStep === i ? 'w-8 bg-turmeric' : 'w-2.5 bg-navy/20 hover:bg-navy/40'
                      }`}
                      aria-label={`Go to step ${i + 1}`}
                    />
                  ))}
                </div>
                <span className="text-xs font-medium text-navy/70">
                  Scroll or tap to preview scene
                </span>
              </div>
            </div>
          </div>

          {/* Right Scrolling 5 Steps */}
          <div className="lg:col-span-6 space-y-8 lg:space-y-12 py-4">
            {copy.howItWorks.steps.map((step, idx) => (
              <StepItem
                key={step.number}
                step={step}
                index={idx}
                isActive={activeStep === idx}
                onInView={() => setActiveStep(idx)}
              />
            ))}
          </div>

        </div>

      </div>
    </section>
  );
};

interface StepItemProps {
  step: typeof copy.howItWorks.steps[0];
  index: number;
  isActive: boolean;
  onInView: () => void;
}

const StepItem: React.FC<StepItemProps> = ({ step, index, isActive, onInView }) => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { amount: 0.55 });

  useEffect(() => {
    if (isInView) {
      onInView();
    }
  }, [isInView, onInView]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.5 }}
      onClick={onInView}
      className={`p-6 sm:p-8 rounded-2xl border-2 transition-all cursor-pointer ${
        isActive
          ? 'bg-navy text-cream border-turmeric shadow-paper-lg scale-[1.02]'
          : 'bg-cream text-navy border-navy/10 hover:border-navy/30'
      }`}
    >
      <div className="flex items-start justify-between gap-4 mb-4">
        <span
          className={`text-2xl sm:text-3xl font-extrabold font-display ${
            isActive ? 'text-turmeric' : 'text-navy/30'
          }`}
        >
          {step.number}
        </span>
        <div
          className={`px-3 py-1 rounded-full text-xs font-bold ${
            isActive ? 'bg-turmeric text-navy' : 'bg-navy/5 text-navy/70'
          }`}
        >
          {isActive ? 'Live in 3D' : 'Tap to focus'}
        </div>
      </div>

      <h3
        className={`text-2xl font-bold font-display mb-2 ${
          isActive ? 'text-cream' : 'text-navy'
        }`}
      >
        {step.title}
      </h3>

      <p className={`text-sm sm:text-base leading-relaxed ${isActive ? 'text-cream/80' : 'text-navy/75'}`}>
        {step.detail}
      </p>

      {step.dictationOrState && (
        <div
          className={`mt-4 p-3 rounded-xl font-mono text-xs ${
            isActive
              ? 'bg-navy-light text-turmeric border border-cream/10'
              : 'bg-cream-paper text-navy/90 border border-navy/10'
          }`}
        >
          &gt; {step.dictationOrState}
        </div>
      )}
    </motion.div>
  );
};

// Fallback visual illustration for reduced-motion or WebGL failure
const StepsFallbackVisual: React.FC<{ activeStep: number }> = ({ activeStep }) => {
  const fallbacks = [
    { title: 'Listening to Voice', sub: 'Pulsing voice orb capturing spoken Hinglish audio stream.', icon: Mic },
    { title: 'Processing Speech', sub: 'Extracting customer, items, prices, and credit from natural speech.', icon: Sparkles },
    { title: 'Structured Chips', sub: 'Splitting into verified fields: Customer, Items, Bill, Paid, Udhaar.', icon: CheckCircle2 },
    { title: 'Confirm Card', sub: 'Instant summary pop-up to check before committing to the ledger.', icon: ArrowRight },
    { title: 'WhatsApp Receipt', sub: 'Prefilled bill ready for 1-tap customer delivery on WhatsApp.', icon: Smartphone },
  ];

  const current = fallbacks[activeStep] || fallbacks[0];
  const Icon = current.icon;

  return (
    <div className="p-8 rounded-2xl bg-cream-paper border-2 border-navy/15 text-center space-y-4 max-w-sm">
      <div className="w-16 h-16 mx-auto rounded-full bg-turmeric flex items-center justify-center text-navy shadow-md">
        <Icon className="w-8 h-8" />
      </div>
      <div>
        <h4 className="font-display font-bold text-lg text-navy">{current.title}</h4>
        <p className="text-xs text-navy/70 mt-1">{current.sub}</p>
      </div>
    </div>
  );
};

const StepsLoadingFallback: React.FC = () => (
  <div className="w-full h-full flex flex-col items-center justify-center animate-pulse">
    <div className="w-14 h-14 rounded-full bg-turmeric/30 mb-2" />
    <span className="text-xs font-semibold text-navy/50">Loading 3D scene...</span>
  </div>
);
