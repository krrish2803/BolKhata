import React from 'react';
import { Navbar } from '../components/Navbar';
import { Hero } from '../components/Hero';
import { Problem } from '../components/Problem';
import { Solution } from '../components/Solution';
import { Features } from '../components/Features';
import { HowItWorks } from '../components/HowItWorks';
import { Benefits } from '../components/Benefits';
import { CtaBand } from '../components/CtaBand';
import { FAQ } from '../components/FAQ';
import { Footer } from '../components/Footer';

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-cream text-navy flex flex-col selection:bg-turmeric selection:text-navy">
      <Navbar />
      <main className="flex-grow">
        <Hero />
        <Problem />
        <Solution />
        <Features />
        <HowItWorks />
        <Benefits />
        <CtaBand />
        <FAQ />
      </main>
      <Footer />
    </div>
  );
};
