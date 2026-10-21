import React, { Suspense, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { copy } from '../content/copy';
import { Mic, ArrowRight } from 'lucide-react';
import { Canvas } from '@react-three/fiber';
import { FloatingCoins } from '../three/Particles';
import { WebGLErrorBoundary, isWebGLAvailable } from './WebGLErrorBoundary';

export const CtaBand: React.FC = () => {
  const [canRenderWebGL, setCanRenderWebGL] = useState(true);

  useEffect(() => {
    setCanRenderWebGL(isWebGLAvailable());
  }, []);

  return (
    <section className="relative py-24 md:py-32 bg-navy text-cream overflow-hidden border-b border-navy/20">
      {/* Background 3D Floating Gold Coins */}
      {canRenderWebGL && (
        <div className="absolute inset-0 pointer-events-none opacity-40">
          <WebGLErrorBoundary fallback={<div />}>
            <Suspense fallback={null}>
              <Canvas
                camera={{ position: [0, 0, 5], fov: 45 }}
                dpr={[1, 1.5]}
                gl={{ alpha: true }}
              >
                <ambientLight intensity={0.9} />
                <directionalLight position={[3, 5, 2]} intensity={1.5} color="#FFF8EC" />
                <FloatingCoins count={16} areaRadius={5} />
              </Canvas>
            </Suspense>
          </WebGLErrorBoundary>
        </div>
      )}

      {/* Glow aura */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-turmeric/15 blur-3xl pointer-events-none" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10 space-y-8">
        <motion.h2
          initial={{ opacity: 0, y: 25 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-4xl sm:text-5xl md:text-6xl font-extrabold font-display text-cream tracking-tight max-w-3xl mx-auto leading-tight"
        >
          {copy.ctaBand.headline}
        </motion.h2>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2"
        >
          <Link
            to="/auth"
            className="inline-flex items-center justify-center gap-3 px-10 py-5 rounded-2xl bg-turmeric hover:bg-turmeric-hover text-navy font-extrabold text-lg shadow-paper-lg hover:shadow-turmeric-glow transition-all active:scale-[0.98]"
          >
            <Mic className="w-6 h-6 text-navy animate-pulse" />
            <span>{copy.ctaBand.buttonText}</span>
            <ArrowRight className="w-5 h-5 text-navy" />
          </Link>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="text-sm text-cream/70 font-medium"
        >
          {copy.ctaBand.subtext}
        </motion.p>
      </div>
    </section>
  );
};
