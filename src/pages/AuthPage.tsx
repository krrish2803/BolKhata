import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mic, ArrowLeft, Lock, Phone, Store, User as UserIcon, Tag, CheckCircle2, ArrowRight, ShieldCheck, AlertCircle, MessageSquare, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const AuthPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { login, signup, startDemoSession } = useAuth();

  // Mode: 'signin' or 'signup'
  const initialMode = searchParams.get('mode') === 'signup' ? 'signup' : 'signin';
  const [mode, setMode] = useState<'signin' | 'signup'>(initialMode);

  // Form states - empty for real accounts by default
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [name, setName] = useState('');
  const [shopName, setShopName] = useState('');
  const [shopType, setShopType] = useState('Kirana / General Store');

  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const switchMode = (newMode: 'signin' | 'signup') => {
    setMode(newMode);
    setError(null);
    setSearchParams({ mode: newMode });
  };

  const handleDemoLaunch = async () => {
    setError(null);
    setDemoLoading(true);
    const res = await startDemoSession();
    setDemoLoading(false);
    if (res.success) {
      navigate('/app');
    } else {
      setError(res.error || 'Failed to start demo session');
    }
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const res = await login(phone, pin);
    setLoading(false);

    if (res.success) {
      navigate('/app');
    } else {
      setError(res.error || 'Failed to sign in');
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const res = await signup({ name, whatsAppNumber: phone, shopName, shopType, pin });
    setLoading(false);

    if (res.success) {
      navigate('/app');
    } else {
      setError(res.error || 'Failed to create account');
    }
  };

  return (
    <div className="min-h-screen bg-cream text-navy flex flex-col justify-between selection:bg-turmeric selection:text-navy">
      {/* Top Navbar */}
      <header className="px-4 sm:px-8 py-5 border-b border-navy/10 bg-cream-paper/70 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm font-semibold text-navy/70 hover:text-navy transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to BolKhata Home</span>
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-navy flex items-center justify-center text-turmeric shadow-sm">
              <Mic className="w-4 h-4 text-turmeric" />
            </div>
            <span className="font-display font-extrabold text-xl text-navy">BolKhata</span>
          </div>
        </div>
      </header>

      {/* Main Authentication Box */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          
          {/* Card Container */}
          <div className="bg-cream-paper rounded-3xl border-2 border-navy/15 shadow-paper-lg p-6 sm:p-8 space-y-6">
            
            {/* Header info */}
            <div className="text-center space-y-2">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-turmeric/20 text-navy text-xs font-bold border border-turmeric/40">
                <ShieldCheck className="w-3.5 h-3.5 text-navy" />
                <span>Secure Voice Ledger Access</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold font-display text-navy">
                {mode === 'signin' ? 'Sign in to your Khata' : 'Open your free Khata'}
              </h1>
              <p className="text-xs sm:text-sm text-navy/70">
                {mode === 'signin'
                  ? 'Access your voice entries, customer udhaar & stock.'
                  : 'Start recording counter sales in natural Hinglish in 10 seconds.'}
              </p>
            </div>

            {/* Mode Switch Tabs */}
            <div className="p-1 rounded-xl bg-navy/5 flex">
              <button
                type="button"
                onClick={() => switchMode('signin')}
                className={`flex-1 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                  mode === 'signin'
                    ? 'bg-navy text-turmeric shadow-sm'
                    : 'text-navy/70 hover:text-navy'
                }`}
              >
                Sign In (लॉग इन)
              </button>
              <button
                type="button"
                onClick={() => switchMode('signup')}
                className={`flex-1 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                  mode === 'signup'
                    ? 'bg-navy text-turmeric shadow-sm'
                    : 'text-navy/70 hover:text-navy'
                }`}
              >
                Create Account (खाता बनाएं)
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 rounded-xl bg-khataRed/10 border border-khataRed/30 text-khataRed text-xs font-semibold flex items-start gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* SIGN IN FORM */}
            <AnimatePresence mode="wait">
              {mode === 'signin' ? (
                <motion.form
                  key="signin-form"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  onSubmit={handleSignIn}
                  className="space-y-4"
                >
                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-navy/70 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <MessageSquare className="w-3.5 h-3.5 text-khataGreen" />
                        <span>WhatsApp Number (व्हाट्सएप नंबर)</span>
                      </span>
                      <span className="text-[10px] text-khataGreen font-semibold lowercase">
                        for receipts
                      </span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-navy/50 text-sm font-semibold">
                        +91
                      </div>
                      <input
                        type="tel"
                        required
                        maxLength={10}
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="98765 43210"
                        className="w-full pl-12 pr-4 py-3 rounded-xl bg-cream border border-navy/20 font-medium text-navy text-sm focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-bold uppercase tracking-wider text-navy/70">
                        4-Digit PIN (पिन)
                      </label>
                      {phone.endsWith('9876543210') && (
                        <span className="text-[11px] text-turmeric-hover font-semibold">
                          Hint: Demo PIN is 1234
                        </span>
                      )}
                    </div>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-navy/40">
                        <Lock className="w-4 h-4" />
                      </div>
                      <input
                        type="password"
                        required
                        maxLength={4}
                        value={pin}
                        onChange={(e) => setPin(e.target.value)}
                        placeholder="••••"
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-cream border border-navy/20 font-mono tracking-widest text-navy text-sm focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || demoLoading}
                    className="w-full py-3.5 px-4 rounded-xl bg-navy hover:bg-navy-light text-turmeric font-extrabold text-sm flex items-center justify-center gap-2 shadow-paper hover:shadow-turmeric-glow transition-all active:scale-[0.98]"
                  >
                    <span>{loading ? 'Opening Khata...' : 'Sign In & Open Counter'}</span>
                    <ArrowRight className="w-4 h-4 text-turmeric" />
                  </button>

                  {/* 1-Click Try the demo button */}
                  <div className="pt-2 border-t border-navy/10 space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="h-[1px] flex-1 bg-navy/15"></div>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-navy/40">or instant demo</span>
                      <div className="h-[1px] flex-1 bg-navy/15"></div>
                    </div>
                    <button
                      type="button"
                      onClick={handleDemoLaunch}
                      disabled={demoLoading || loading}
                      className="w-full py-3.5 px-4 rounded-xl bg-turmeric hover:bg-turmeric-hover text-navy font-extrabold text-sm flex items-center justify-center gap-2 shadow-paper hover:shadow-turmeric-glow transition-all active:scale-[0.98]"
                    >
                      <Sparkles className="w-4 h-4 text-navy fill-navy/30" />
                      <span>{demoLoading ? 'Creating Sample Workspace...' : 'Try the demo (1-Click)'}</span>
                      <ArrowRight className="w-4 h-4 text-navy" />
                    </button>
                    <p className="text-[11px] text-center text-navy/70">
                      Creates a fresh 24h sample workspace with seeded customers & stock. No phone or PIN needed.
                    </p>
                  </div>
                </motion.form>
              ) : (
                /* SIGN UP FORM */
                <motion.form
                  key="signup-form"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  onSubmit={handleSignUp}
                  className="space-y-3.5"
                >
                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-navy/70">
                      Your Name (आपका नाम)
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-navy/40">
                        <UserIcon className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Ramesh Sharma"
                        className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-cream border border-navy/20 font-medium text-navy text-sm focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-navy/70 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <MessageSquare className="w-3.5 h-3.5 text-khataGreen" />
                        <span>WhatsApp Number (व्हाट्सएप नंबर)</span>
                      </span>
                      <span className="text-[10px] text-khataGreen font-semibold lowercase">
                        for receipts
                      </span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-navy/50 text-sm font-semibold">
                        +91
                      </div>
                      <input
                        type="tel"
                        required
                        maxLength={10}
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        placeholder="98765 43210"
                        className="w-full pl-12 pr-4 py-2.5 rounded-xl bg-cream border border-navy/20 font-medium text-navy text-sm focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-navy/70">
                      Shop / Business Name (दुकान का नाम)
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-navy/40">
                        <Store className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        required
                        value={shopName}
                        onChange={(e) => setShopName(e.target.value)}
                        placeholder="e.g. Sharma Cloth Store"
                        className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-cream border border-navy/20 font-medium text-navy text-sm focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-navy/70">
                      Shop Type (दुकान का प्रकार)
                    </label>
                    <select
                      value={shopType}
                      onChange={(e) => setShopType(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-xl bg-cream border border-navy/20 font-medium text-navy text-sm focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner"
                    >
                      <option value="Kirana / General Store">Kirana / General Store (किराना)</option>
                      <option value="Clothing & Garments">Clothing & Garments (कपड़े की दुकान)</option>
                      <option value="Hardware & Electrical">Hardware & Electrical (हार्डवेयर)</option>
                      <option value="Mandi Trader">Mandi Wholesale Trader (मंडी आढ़त)</option>
                      <option value="Other Retail">Other Retail Counter</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-navy/70">
                      Set 4-Digit Security PIN (4-अंकों का पिन बनाएं)
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-navy/40">
                        <Lock className="w-4 h-4" />
                      </div>
                      <input
                        type="password"
                        required
                        maxLength={4}
                        value={pin}
                        onChange={(e) => setPin(e.target.value)}
                        placeholder="Choose 4 digits (e.g. 5892)"
                        className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-cream border border-navy/20 font-mono tracking-widest text-navy text-sm focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner"
                      />
                    </div>
                    <p className="text-[10px] text-navy/50">
                      Trivial PINs like 1234, 0000, 1111 or sequential numbers are rejected for security.
                    </p>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || demoLoading}
                    className="w-full py-3.5 px-4 rounded-xl bg-navy hover:bg-navy-light text-turmeric font-extrabold text-sm flex items-center justify-center gap-2 shadow-paper transition-all active:scale-[0.98] mt-2"
                  >
                    <span>{loading ? 'Creating...' : 'Register Real Account'}</span>
                    <ArrowRight className="w-4 h-4 text-turmeric" />
                  </button>

                  {/* 1-Click Try the demo button on sign-up as well */}
                  <div className="pt-2 border-t border-navy/10 space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="h-[1px] flex-1 bg-navy/15"></div>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-navy/40">or test first</span>
                      <div className="h-[1px] flex-1 bg-navy/15"></div>
                    </div>
                    <button
                      type="button"
                      onClick={handleDemoLaunch}
                      disabled={demoLoading || loading}
                      className="w-full py-3.5 px-4 rounded-xl bg-turmeric hover:bg-turmeric-hover text-navy font-extrabold text-sm flex items-center justify-center gap-2 shadow-paper hover:shadow-turmeric-glow transition-all active:scale-[0.98]"
                    >
                      <Sparkles className="w-4 h-4 text-navy fill-navy/30" />
                      <span>{demoLoading ? 'Creating Sample Workspace...' : 'Try the demo (1-Click)'}</span>
                      <ArrowRight className="w-4 h-4 text-navy" />
                    </button>
                  </div>
                </motion.form>
              )}
            </AnimatePresence>

          </div>

          {/* Bottom Security Note */}
          <div className="text-center mt-6 text-xs text-navy/60 space-y-1">
            <p>Demo accounts use sample data. Don't enter real customer details.</p>
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-xs text-navy/50 border-t border-navy/10">
        © 2026 BolKhata · Built for the No Hands: The Wispr Challenge
      </footer>
    </div>
  );
};
