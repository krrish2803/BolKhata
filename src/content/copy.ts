export interface CopyContent {
  meta: {
    title: string;
    description: string;
  };
  navbar: {
    brand: string;
    brandHindi: string;
    links: { label: string; href: string }[];
    ctaText: string;
    ctaHref: string;
  };
  hero: {
    badge: string;
    headline: string;
    subheadline: string;
    primaryCta: string;
    secondaryCta: string;
    dictationExample: string;
  };
  problem: {
    sectionTag: string;
    title: string;
    points: {
      title: string;
      description: string;
    }[];
    kicker: string;
    statPlaceholder: string;
  };
  solution: {
    sectionTag: string;
    title: string;
    description: string;
    spokenSentence: string;
    parsedEntry: {
      customer: string;
      items: string;
      total: string;
      paid: string;
      due: string;
      status: string;
    };
  };
  features: {
    sectionTag: string;
    title: string;
    subtitle: string;
    cards: {
      id: string;
      title: string;
      tagline: string;
      description: string;
      badge?: string;
    }[];
  };
  howItWorks: {
    sectionTag: string;
    title: string;
    subtitle: string;
    steps: {
      number: string;
      title: string;
      detail: string;
      dictationOrState?: string;
    }[];
  };
  benefits: {
    sectionTag: string;
    title: string;
    subtitle: string;
    blocks: {
      title: string;
      description: string;
    }[];
    shopTypesNote: string;
  };
  ctaBand: {
    headline: string;
    buttonText: string;
    subtext: string;
  };
  faq: {
    sectionTag: string;
    title: string;
    subtitle: string;
    items: {
      question: string;
      answer: string;
    }[];
  };
  footer: {
    brand: string;
    tagline: string;
    challengeNote: string;
    copyright: string;
  };
}

export const copy: CopyContent = {
  meta: {
    title: "BolKhata — Bolo. Likho mat.",
    description: "Voice-entry ledger for small shop owners in India. Dictate in Hinglish, update udhaar and stock, and send WhatsApp receipts."
  },
  navbar: {
    brand: "BolKhata",
    brandHindi: "बोलखाता",
    links: [
      { label: "Problem", href: "#problem" },
      { label: "Solution", href: "#solution" },
      { label: "Features", href: "#features" },
      { label: "How It Works", href: "#how-it-works" },
      { label: "FAQ", href: "#faq" }
    ],
    ctaText: "Try the demo",
    ctaHref: "/auth"
  },
  hero: {
    badge: "Built for Indian Counter Speed",
    headline: "Bolo. Likho mat.",
    subheadline: "Say your sale out loud. BolKhata writes the ledger, updates the udhaar, and sends the WhatsApp receipt.",
    primaryCta: "Try the demo",
    secondaryCta: "See how it works",
    dictationExample: 'Try saying: "Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar"'
  },
  problem: {
    sectionTag: "The Reality At The Counter",
    title: "The khata is still on paper.",
    points: [
      {
        title: "Entries get written late, or not at all",
        description: "When four customers are waiting at the counter, nobody has time to open the red diary and pen down every detail."
      },
      {
        title: "Udhaar balances get forgotten or disputed",
        description: "Pages get misplaced, old pencil marks fade, and neither you nor the customer can agree on the last balance."
      },
      {
        title: "Typing into billing apps is too slow",
        description: "Complex dropdowns, inventory SKUs, and on-screen keyboards break counter rhythm, so owners go right back to the diary."
      }
    ],
    kicker: "Most small shops run on a notebook and memory. That works until it doesn't.",
    statPlaceholder: "[add real number after testing] % of counter disputes happen due to unrecorded informal credit"
  },
  solution: {
    sectionTag: "Voice-First Accounting",
    title: "Just say it. BolKhata handles the rest.",
    description: "You speak naturally in everyday bazaar Hinglish. Our voice intelligence extracts items, prices, payments, and credit balances in real time.",
    spokenSentence: "“Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar”",
    parsedEntry: {
      customer: "Sharma ji (Ramesh)",
      items: "2x Shirt, 1x Trouser",
      total: "₹4,200",
      paid: "₹2,000 (Cash)",
      due: "₹2,200 (Udhaar added)",
      status: "Verified & Stock deducted"
    }
  },
  features: {
    sectionTag: "Capabilities",
    title: "Everything your bahi-khata needs, powered by voice.",
    subtitle: "Built without bloated ERP menus. Pure speed for busy storefronts.",
    cards: [
      {
        id: "hinglish",
        title: "Speaks Hinglish",
        tagline: "Natural conversational speech",
        description: "Understands mixed Hindi and English seamlessly, including Indian number spoken formats like 'pachis sau', 'dedh hazaar', and 'do hazaar'."
      },
      {
        id: "confirm",
        title: "Confirm before save",
        tagline: "Zero accidental mistakes",
        description: "Shows exactly what it understood before anything commits. Fix any field on the fly simply by dictating a correction."
      },
      {
        id: "udhaar",
        title: "Udhaar tracking",
        tagline: "Crystal-clear balances",
        description: "Maintains a running balance per customer with a clear paid vs due ledger breakdown, so no rupee ever slips through the cracks."
      },
      {
        id: "stock",
        title: "Stock updates",
        tagline: "Automatic inventory deduction",
        description: "Items sold reduce stock counts automatically the moment a voice sale is confirmed. No double entry needed."
      },
      {
        id: "receipts",
        title: "WhatsApp receipts",
        tagline: "Instant trust on the phone",
        description: "Opens WhatsApp with a professional receipt text prefilled with itemized breakdown and updated balance. One tap to send."
      },
      {
        id: "ask",
        title: "Ask your ledger",
        tagline: "Voice query your accounts",
        description: "Ask aloud anytime: 'Sharma ji ka kitna baaki hai?' or 'Aaj ka total cash kitna hua?' and receive instant spoken and visual answers."
      }
    ]
  },
  howItWorks: {
    sectionTag: "Step by Step",
    title: "How it works",
    subtitle: "From voice in the air to a stamped receipt in 5 simple seconds.",
    steps: [
      {
        number: "01",
        title: "Speak the sale",
        detail: "Tap the mic and talk just like you speak to your helper or customer in natural Hinglish.",
        dictationOrState: '“Sharma ji ko do shirt, ek trouser...”'
      },
      {
        number: "02",
        title: "BolKhata understands it",
        detail: "Our speech model processes the audio stream and translates spoken slang into structured ledger items.",
        dictationOrState: "Detecting: Customer, Items, Bill Amount"
      },
      {
        number: "03",
        title: "Check the entry",
        detail: "A clean summary card pops up instantly with Customer, Items, Total, Paid, and Due highlighted in color.",
        dictationOrState: "₹4,200 Bill · ₹2,000 Paid · ₹2,200 Due"
      },
      {
        number: "04",
        title: "Save to the ledger",
        detail: "Tap confirm or say 'Theek hai'. Customer credit history and inventory counters update instantly.",
        dictationOrState: "Ledger committed · Stock updated"
      },
      {
        number: "05",
        title: "Send the receipt on WhatsApp",
        detail: "BolKhata launches WhatsApp with the pre-formatted bill ready. One tap sends it straight to the customer's chat.",
        dictationOrState: "WhatsApp opened · 1-tap send"
      }
    ]
  },
  benefits: {
    sectionTag: "Why Shop Owners Love It",
    title: "Built for the counter, not the office.",
    subtitle: "Designed around the chaotic reality of high-footfall Indian retail.",
    blocks: [
      {
        title: "Saves time at the counter",
        description: "No typing, no squinting at microscopic dropdowns, no searching through paper diaries while customers wait in line."
      },
      {
        title: "Fewer udhaar disputes",
        description: "Every credit entry is timestamped, itemized, and backed by a WhatsApp receipt sent to the customer on the spot."
      },
      {
        title: "Always know your stock",
        description: "Your quantity drops the moment you dictate a sale, preventing embarrassing stockouts and over-selling."
      },
      {
        title: "Works on the phone you already have",
        description: "Runs directly in your mobile browser. No costly POS hardware, thermal printers, or separate barcode scanners required."
      }
    ],
    shopTypesNote: "Specially tailored for shops that run on a paper khata: clothing stores, kirana & general stores, hardware & electricals, and mandi wholesale traders."
  },
  ctaBand: {
    headline: "Close the diary. Open BolKhata.",
    buttonText: "Try the demo",
    subtext: "Demo accounts use sample data. Don't enter real customer details."
  },
  faq: {
    sectionTag: "Got Questions?",
    title: "Frequently Asked Questions",
    subtitle: "Clear answers for busy shop owners.",
    items: [
      {
        question: "Does it understand Hinglish?",
        answer: "Yes, it is built specifically for mixed Hindi and English, including numbers said in words like 'pachis sau', 'paanch hazaar', or 'saadhe teen sau'. Tell it if it gets something wrong and it corrects the entry."
      },
      {
        question: "What if it hears something wrong?",
        answer: "Every entry shows a confirm card first before touching your books. You can fix any field or simply dictate a correction like 'shirt nahi, kurti hai' before it is saved."
      },
      {
        question: "Do I need to install anything?",
        answer: "The demo runs straight in your web browser with zero installation. [Note: dictation uses your device's voice input.]"
      },
      {
        question: "How do receipts work?",
        answer: "BolKhata opens WhatsApp with the receipt message already formatted and typed out. You just tap send. No expensive WhatsApp Business API or verification needed."
      },
      {
        question: "Is my data safe?",
        answer: "The interactive demo runs on client-side sample data only. [Placeholder: add a real privacy statement before handling real customer data.]"
      },
      {
        question: "Which shops is it for?",
        answer: "Any small shop that records sales or udhaar on paper: clothing & saree stores, kirana and groceries, electrical and hardware merchants, and mandi traders."
      },
      {
        question: "Is it free?",
        answer: "The interactive demo is completely free to test. [Placeholder for pricing.]"
      }
    ]
  },
  footer: {
    brand: "BolKhata",
    tagline: "Bolo. Likho mat. Voice-first accounting for India's retail backbone.",
    challengeNote: "Built for the No Hands: The Wispr Challenge",
    copyright: "© 2026 BolKhata. All rights reserved."
  }
};
