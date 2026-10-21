import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Volume2, CheckCircle2, Send, ShoppingBag, User, ArrowRight, RefreshCw, Sparkles } from 'lucide-react';

interface DictationPreset {
  speech: string;
  customer: string;
  phone: string;
  items: { name: string; qty: number; price: number }[];
  total: number;
  paid: number;
  due: number;
  stockAlert?: string;
}

const PRESETS: DictationPreset[] = [
  {
    speech: "Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar",
    customer: "Ramesh Sharma",
    phone: "+91 98765 43210",
    items: [
      { name: "Cotton Formal Shirt", qty: 2, price: 2400 },
      { name: "Slim Fit Trouser", qty: 1, price: 1800 },
    ],
    total: 4200,
    paid: 2000,
    due: 2200,
    stockAlert: "Stock updated: Shirt (14 left), Trouser (8 left)",
  },
  {
    speech: "Verma ji ne paanch kilo basmati chawal aur do tel liya, 1450 total, poora cash de diya",
    customer: "Suresh Verma (Kirana)",
    phone: "+91 98111 22334",
    items: [
      { name: "Basmati Rice (5kg)", qty: 1, price: 750 },
      { name: "Mustard Oil (1L)", qty: 2, price: 700 },
    ],
    total: 1450,
    paid: 1450,
    due: 0,
    stockAlert: "Stock updated: Basmati (22 packs left)",
  },
  {
    speech: "Gupta hardware ko teen box screw aur do drill bit diye, pachis sau bill, hazaar diya baaki udhaar",
    customer: "Gupta Hardware & Tools",
    phone: "+91 99223 88441",
    items: [
      { name: "Steel Screws (Box of 100)", qty: 3, price: 1200 },
      { name: "Masonry Drill Bit 8mm", qty: 2, price: 1300 },
    ],
    total: 2500,
    paid: 1000,
    due: 1500,
    stockAlert: "Stock updated: Screws (19 boxes left)",
  },
];

export const InteractiveLedgerHeroCard: React.FC = () => {
  const [presetIndex, setPresetIndex] = useState(0);
  const [stage, setStage] = useState<'listening' | 'parsed' | 'saved' | 'sent'>('parsed');
  const [isTyping, setIsTyping] = useState(false);
  const [displayedText, setDisplayedText] = useState(PRESETS[0].speech);

  const active = PRESETS[presetIndex];

  // Auto-typing animation when switching presets
  const triggerPreset = (idx: number) => {
    setPresetIndex(idx);
    setStage('listening');
    setIsTyping(true);
    setDisplayedText('');

    const target = PRESETS[idx].speech;
    let charIdx = 0;
    const interval = setInterval(() => {
      charIdx++;
      setDisplayedText(target.slice(0, charIdx));
      if (charIdx >= target.length) {
        clearInterval(interval);
        setIsTyping(false);
        setTimeout(() => setStage('parsed'), 400);
      }
    }, 18);
  };

  const handleConfirm = () => {
    setStage('saved');
    setTimeout(() => {
      setStage('sent');
    }, 900);
  };

  const handleReset = () => {
    const nextIdx = (presetIndex + 1) % PRESETS.length;
    triggerPreset(nextIdx);
  };

  return (
    <div className="w-full max-w-lg mx-auto select-none">
      {/* Decorative Outer Frame with authentic bahi-khata feel */}
      <div className="relative rounded-3xl bg-navy p-1.5 shadow-2xl border-4 border-navy/20">
        
        {/* Glow pill badge */}
        <div className="absolute -top-3.5 right-6 z-20 flex items-center gap-1.5 px-3 py-1 rounded-full bg-turmeric text-navy font-bold text-xs shadow-md">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Interactive Counter</span>
        </div>

        {/* Card Body */}
        <div className="rounded-[22px] bg-cream-paper p-5 sm:p-6 space-y-4 overflow-hidden border border-navy/10">
          
          {/* Top Bar: Preset Switcher & Voice Status */}
          <div className="flex items-center justify-between border-b border-navy/10 pb-3">
            <div className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-full ${isTyping || stage === 'listening' ? 'bg-khataRed animate-ping' : 'bg-khataGreen'}`} />
              <span className="text-xs font-bold uppercase tracking-wider text-navy/70">
                {isTyping ? 'Transcribing Voice...' : stage === 'sent' ? 'Receipt Sent ✓' : 'Live Counter Parser'}
              </span>
            </div>

            <button
              onClick={handleReset}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-navy/5 hover:bg-navy/10 text-navy text-xs font-semibold transition-colors"
              title="Try next example"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Try another sample</span>
            </button>
          </div>

          {/* Voice Input Box */}
          <div className="p-3.5 rounded-xl bg-cream border-2 border-turmeric/40 shadow-inner relative space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-bold text-navy/50">
              <span className="flex items-center gap-1">
                <Mic className="w-3.5 h-3.5 text-turmeric-hover" />
                <span>Shopkeeper Dictated (Hinglish):</span>
              </span>
              <span className="font-mono text-navy/40">Mic Active</span>
            </div>
            
            <p className="text-sm font-semibold text-navy leading-snug italic font-display min-h-[42px]">
              "{displayedText}"
            </p>

            {/* Audio Waveform Simulator */}
            <div className="flex items-center gap-1 pt-1 h-3">
              {[4, 12, 6, 16, 9, 20, 14, 8, 18, 11, 5, 14, 8, 16, 10, 4].map((h, i) => (
                <div
                  key={i}
                  className={`w-1 rounded-full transition-all duration-200 ${isTyping ? 'bg-turmeric' : 'bg-navy/15'}`}
                  style={{ height: isTyping ? `${h}px` : '4px' }}
                />
              ))}
            </div>
          </div>

          {/* Live Extracted Digital Ledger Card */}
          <div className="rounded-xl bg-navy text-cream p-4 space-y-3 shadow-md relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-cream/10 pb-2.5 text-xs">
              <div className="flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-turmeric" />
                <span className="font-bold text-cream font-display text-sm">{active.customer}</span>
              </div>
              <span className="font-mono text-[11px] text-cream/60">{active.phone}</span>
            </div>

            {/* Items row */}
            <div className="space-y-1 text-xs">
              {active.items.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between text-cream/80">
                  <span className="flex items-center gap-1.5">
                    <ShoppingBag className="w-3 h-3 text-turmeric/80" />
                    <span>{item.qty}x {item.name}</span>
                  </span>
                  <span className="font-mono text-cream font-medium">₹{item.price.toLocaleString()}</span>
                </div>
              ))}
            </div>

            {/* Financial Ledger Breakdown */}
            <div className="pt-2 border-t border-cream/10 grid grid-cols-3 gap-2 text-center">
              <div className="p-2 rounded-lg bg-cream/5">
                <div className="text-[10px] uppercase font-bold text-cream/50">Total Bill</div>
                <div className="text-sm font-extrabold text-turmeric font-display">₹{active.total.toLocaleString()}</div>
              </div>
              
              <div className="p-2 rounded-lg bg-khataGreen/15 border border-khataGreen/30">
                <div className="text-[10px] uppercase font-bold text-khataGreen">Paid (Jama)</div>
                <div className="text-sm font-extrabold text-khataGreen font-display">₹{active.paid.toLocaleString()}</div>
              </div>

              <div className="p-2 rounded-lg bg-khataRed/15 border border-khataRed/30">
                <div className="text-[10px] uppercase font-bold text-khataRed">Udhaar (Due)</div>
                <div className="text-sm font-extrabold text-khataRed font-display">₹{active.due.toLocaleString()}</div>
              </div>
            </div>

            {/* Micro Stock Status */}
            {active.stockAlert && (
              <div className="text-[11px] text-cream/60 flex items-center justify-between pt-1">
                <span>📦 {active.stockAlert}</span>
                <span className="text-khataGreen font-medium">✓ Ledger in sync</span>
              </div>
            )}
          </div>

          {/* Interactive Action Controls */}
          <div className="space-y-2 pt-1">
            <AnimatePresence mode="wait">
              {stage === 'parsed' && (
                <motion.div
                  key="confirm"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex gap-2.5"
                >
                  <button
                    onClick={handleConfirm}
                    className="flex-1 py-3 px-4 rounded-xl bg-turmeric hover:bg-turmeric-hover text-navy font-extrabold text-sm flex items-center justify-center gap-2 shadow-sm transition-all active:scale-[0.98]"
                  >
                    <CheckCircle2 className="w-4 h-4 text-navy" />
                    <span>Confirm & Update Ledger</span>
                  </button>
                  <button
                    onClick={handleReset}
                    className="p-3 rounded-xl bg-navy/5 hover:bg-navy/10 text-navy font-bold text-xs"
                    title="Change example"
                  >
                    Next
                  </button>
                </motion.div>
              )}

              {stage === 'saved' && (
                <motion.div
                  key="saved"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  className="py-3 px-4 rounded-xl bg-khataGreen text-white font-bold text-sm flex items-center justify-center gap-2"
                >
                  <CheckCircle2 className="w-4 h-4 text-white animate-spin" />
                  <span>Ledger committed · Opening WhatsApp...</span>
                </motion.div>
              )}

              {stage === 'sent' && (
                <motion.div
                  key="sent"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3.5 rounded-xl bg-[#DCF8C6] border border-[#075E54]/20 space-y-2 text-[#075E54]"
                >
                  <div className="flex items-center justify-between font-bold text-xs">
                    <span className="flex items-center gap-1.5">
                      <Send className="w-3.5 h-3.5 text-[#075E54]" />
                      <span>WhatsApp Receipt Ready</span>
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#075E54] text-white">Prefilled</span>
                  </div>
                  <div className="text-[11px] font-mono text-[#0F1B2D]/90 bg-white/70 p-2 rounded-lg border border-black/5">
                    "BolKhata Receipt for {active.customer}: Total ₹{active.total}, Paid ₹{active.paid}, Baaki Udhaar ₹{active.due}. Dhanyawaad!"
                  </div>
                  <div className="flex items-center justify-between pt-1 text-[11px]">
                    <a
                      href={`https://api.whatsapp.com/send?text=${encodeURIComponent(
                        `BolKhata Receipt for ${active.customer}:\nBill: ₹${active.total}\nPaid: ₹${active.paid}\nBaaki Udhaar: ₹${active.due}\nDhanyawaad!`
                      )}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-bold underline text-[#075E54] hover:opacity-80"
                    >
                      Tap to open WhatsApp &rarr;
                    </a>
                    <button
                      onClick={handleReset}
                      className="font-semibold text-navy/60 hover:text-navy text-[11px]"
                    >
                      Try next sale
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Quick preset selector buttons */}
          <div className="pt-2 border-t border-navy/5 flex items-center justify-between text-xs text-navy/60">
            <span>Sample sales:</span>
            <div className="flex gap-1.5">
              {PRESETS.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => triggerPreset(idx)}
                  className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                    presetIndex === idx
                      ? 'bg-navy text-turmeric'
                      : 'bg-navy/5 text-navy/70 hover:bg-navy/10'
                  }`}
                >
                  {idx === 0 ? 'Cloth shop' : idx === 1 ? 'Kirana' : 'Hardware'}
                </button>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
