import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { copy } from '../content/copy';
import { Menu, X, ArrowRight, Mic } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-cream/95 backdrop-blur-md border-b border-navy/10 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Logo */}
        <a href="#" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-navy flex items-center justify-center text-turmeric shadow-md group-hover:scale-105 transition-transform">
            <Mic className="w-5 h-5 text-turmeric" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-baseline gap-1.5">
              <span className="font-display font-extrabold text-2xl tracking-tight text-navy">
                {copy.navbar.brand}
              </span>
              <span className="text-xs font-semibold px-1.5 py-0.5 rounded bg-turmeric/20 text-navy/80">
                {copy.navbar.brandHindi}
              </span>
            </div>
            <span className="text-[10px] text-navy/60 font-medium tracking-wide -mt-0.5">
              Voice-entry ledger
            </span>
          </div>
        </a>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-8">
          {copy.navbar.links.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm font-medium text-navy/75 hover:text-navy hover:underline underline-offset-8 decoration-turmeric decoration-2 transition-colors"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-4">
          <Link
            to={copy.navbar.ctaHref}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-turmeric hover:bg-turmeric-hover text-navy font-bold text-sm tracking-wide shadow-paper hover:shadow-turmeric-glow transition-all active:scale-95"
          >
            <span>{copy.navbar.ctaText}</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Mobile menu button */}
        <div className="flex md:hidden items-center gap-3">
          <Link
            to={copy.navbar.ctaHref}
            className="px-3.5 py-2 rounded-lg bg-turmeric text-navy font-bold text-xs"
          >
            Demo
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg bg-navy/5 text-navy hover:bg-navy/10"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-cream border-b border-navy/10 px-4 pt-3 pb-6 space-y-3 animate-in fade-in slide-in-from-top-2">
          {copy.navbar.links.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 text-base font-semibold text-navy hover:bg-turmeric/10 rounded-lg"
            >
              {link.label}
            </a>
          ))}
          <div className="pt-2">
            <Link
              to={copy.navbar.ctaHref}
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center justify-center gap-2 w-full px-5 py-3 rounded-xl bg-navy text-turmeric font-bold text-sm shadow-md"
            >
              <span>{copy.navbar.ctaText}</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
