import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Mic,
  ArrowLeft,
  Send,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Plus,
  Trash2,
  RefreshCw,
  BookOpen,
  Users,
  Boxes,
  HelpCircle,
  ShoppingBag,
  Info,
  History,
  Undo2,
  MessageSquare,
  Sparkles,
} from 'lucide-react';

interface DraftLine {
  itemId?: string | null;
  name: string;
  qty: number;
  unitPrice: number;
  lineTotal: number;
  isAssumedPrice?: boolean;
}

interface DraftIssue {
  field: string;
  code: string;
  message: string;
  severity: 'error' | 'warning';
}

interface DraftData {
  draftId: string;
  rawText: string;
  customer?: { id?: string | null; name: string; isNew?: boolean; phone?: string | null };
  lines: DraftLine[];
  statedTotal?: number | null;
  computedTotal: number;
  listPrice?: number;
  discount?: number;
  total: number;
  paid: number;
  due: number;
  issues: DraftIssue[];
  canSave: boolean;
  modelInfo?: {
    source?: string;
    model?: string;
    latencyMs?: number;
    isFallback?: boolean;
    cached?: boolean;
  };
}

interface Customer {
  id: string;
  name: string;
  phone?: string;
  balance: number;
}

interface Item {
  id: string;
  name: string;
  price: number;
  stock: number;
}

interface LedgerEntry {
  id: string;
  customerName: string;
  lines: { name: string; qty: number; unitPrice: number; lineTotal: number }[];
  total: number;
  paid: number;
  due: number;
  rawText?: string;
  createdAt: string;
}

export const AppPage: React.FC = () => {
  // Session & workspace
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);

  // Workspace lists
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [items, setItems] = useState<Item[]>([]);

  // Tabs: 'entry' | 'ledger' | 'customers' | 'stock' | 'ask'
  const [activeTab, setActiveTab] = useState<'entry' | 'ledger' | 'customers' | 'stock' | 'ask'>('entry');

  // Feature 2: Ask Your Ledger state
  const [askQuestion, setAskQuestion] = useState('Sharma ji ka kitna baaki hai?');
  const [isAsking, setIsAsking] = useState(false);
  const [askResult, setAskResult] = useState<{
    answer: string;
    facts: Record<string, any>;
    sourceBadge?: string;
    isAmbiguous?: boolean;
    clarificationQuestion?: string;
    candidates?: string[];
  } | null>(null);

  // Parse & Confirm State
  const defaultSaleText = "Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar";
  const [inputText, setInputText] = useState(defaultSaleText);
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);

  // Active Draft
  const [draft, setDraft] = useState<DraftData | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [savedReceiptUrl, setSavedReceiptUrl] = useState<string | null>(null);
  const [updatedBalanceNotice, setUpdatedBalanceNotice] = useState<string | null>(null);

  // Correction by Voice (Feature 1)
  const [correctionText, setCorrectionText] = useState('');
  const [isCorrecting, setIsCorrecting] = useState(false);
  const [correctionDiffs, setCorrectionDiffs] = useState<{ field: string; before: any; after: any }[]>([]);
  const [clarifyingQuestion, setClarifyingQuestion] = useState<{ question: string; options: string[] } | null>(null);
  const [correctionCount, setCorrectionCount] = useState(0);

  // Feature 4: Fuzzy Customer Match state
  const [fuzzyWarning, setFuzzyWarning] = useState<string | null>(null);
  const [fuzzyCandidates, setFuzzyCandidates] = useState<Customer[]>([]);

  // Feature 5: Reminder Modal state
  const [reminderModal, setReminderModal] = useState<{
    customer: Customer;
    tone: 'polite' | 'firm';
    text: string;
    waUrl: string;
    loading: boolean;
  } | null>(null);

  // Feature 6: Daily Summary state
  const [dailySummary, setDailySummary] = useState<{
    date: string;
    entriesCount: number;
    totalSales: number;
    cashCollected: number;
    totalUdhaarGiven: number;
    topCustomer?: string | null;
    topItem?: string | null;
    narrative: string;
  } | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);

  // Undo Last Entry State
  const [isUndoing, setIsUndoing] = useState(false);
  const [undoNotice, setUndoNotice] = useState<string | null>(null);

  // Customer Phone Edit State
  const [editingPhoneCustId, setEditingPhoneCustId] = useState<string | null>(null);
  const [phoneInputVal, setPhoneInputVal] = useState('');
  const [isSavingPhone, setIsSavingPhone] = useState(false);

  const handleUndoLastEntry = async () => {
    if (!confirm("Are you sure you want to undo the last saved entry? This will reverse the customer's balance and restore item stock.")) {
      return;
    }
    try {
      setIsUndoing(true);
      setUndoNotice(null);
      const res = await fetch('/api/entries/undo', {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to undo entry');
      }
      const data = await res.json();
      setUndoNotice(data.message);
      await loadWorkspaceData();
    } catch (e: any) {
      alert(e.message || 'Error undoing entry');
    } finally {
      setIsUndoing(false);
    }
  };

  const handleSavePhone = async (customerId: string) => {
    if (!phoneInputVal.trim()) return;
    try {
      setIsSavingPhone(true);
      const res = await fetch(`/api/customers/${customerId}/phone`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ phone: phoneInputVal.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to update phone');
      }
      setEditingPhoneCustId(null);
      setPhoneInputVal('');
      await loadWorkspaceData();
    } catch (e: any) {
      alert(e.message || 'Error updating phone');
    } finally {
      setIsSavingPhone(false);
    }
  };

  const loadDailySummary = async () => {
    try {
      setIsSummaryLoading(true);
      const res = await fetch('/api/summary/today', { credentials: 'include' });
      if (res.ok) {
        setDailySummary(await res.json());
      }
    } catch (e) {
      console.error('Error fetching daily summary:', e);
    } finally {
      setIsSummaryLoading(false);
    }
  };

  const fetchReminder = async (customer: Customer, tone: 'polite' | 'firm') => {
    try {
      setReminderModal({
        customer,
        tone,
        text: 'Generating reminder draft...',
        waUrl: '',
        loading: true,
      });
      const res = await fetch(`/api/customers/${customer.id}/reminder?tone=${tone}`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Could not fetch reminder');
      const data = await res.json();
      setReminderModal({
        customer,
        tone,
        text: data.text,
        waUrl: data.waUrl,
        loading: false,
      });
    } catch (e: any) {
      alert(e.message || 'Error loading reminder draft');
      setReminderModal(null);
    }
  };

  const handleCorrection = async (textToApply?: string) => {
    const text = (textToApply || correctionText).trim();
    if (!text || !draft) return;
    try {
      setIsCorrecting(true);
      setClarifyingQuestion(null);
      const res = await fetch(`/api/drafts/${draft.draftId}/correct`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to apply correction');
      }
      const data = await res.json();
      if (data.isAmbiguous && data.clarificationQuestion) {
        setClarifyingQuestion({
          question: data.clarificationQuestion,
          options: data.clarificationOptions || [],
        });
      } else {
        setDraft(data.draft);
        setCorrectionDiffs(data.changes || []);
        setCorrectionCount(data.correctionCount || 0);
        setCorrectionText('');
      }
    } catch (e: any) {
      alert(e.message || 'Error applying correction');
    } finally {
      setIsCorrecting(false);
    }
  };

  const handleDirectPatch = async (operations: any[]) => {
    if (!draft || !operations || operations.length === 0) return;
    try {
      setIsCorrecting(true);
      setClarifyingQuestion(null);
      const res = await fetch(`/api/drafts/${draft.draftId}/patch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ operations }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to apply patch');
      }
      const data = await res.json();
      setDraft(data.draft);
      setCorrectionDiffs(data.changes || []);
      setCorrectionCount(data.correctionCount || 0);
    } catch (e: any) {
      alert(e.message || 'Error applying patch');
    } finally {
      setIsCorrecting(false);
    }
  };

  const handleAsk = async (questionToAsk?: string) => {
    const q = (questionToAsk || askQuestion).trim();
    if (!q) return;
    try {
      setIsAsking(true);
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to query ledger');
      }
      const data = await res.json();
      setAskResult(data);
    } catch (e: any) {
      alert(e.message || 'Error asking ledger');
    } finally {
      setIsAsking(false);
    }
  };


  // Initialize Demo Session
  const initSession = async () => {
    try {
      setSessionLoading(true);
      const res = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Could not initialize session');
      const data = await res.json();
      setWorkspaceId(data.workspaceId);
      await loadWorkspaceData();
    } catch (err: any) {
      console.warn('Session init warning (using client fallback if backend not running):', err);
    } finally {
      setSessionLoading(false);
    }
  };

  const loadWorkspaceData = async () => {
    try {
      const [ledgerRes, custRes, itemRes] = await Promise.all([
        fetch('/api/ledger', { credentials: 'include' }),
        fetch('/api/customers', { credentials: 'include' }),
        fetch('/api/items', { credentials: 'include' }),
      ]);
      if (ledgerRes.ok) setLedger(await ledgerRes.json());
      if (custRes.ok) setCustomers(await custRes.json());
      if (itemRes.ok) setItems(await itemRes.json());
      await loadDailySummary();
    } catch (e) {
      console.error('Error fetching workspace lists:', e);
    }
  };

  useEffect(() => {
    initSession();
  }, []);

  // Handle "Read it" (POST /api/parse)
  const handleParse = async () => {
    if (!inputText.trim()) return;
    setIsParsing(true);
    setParseError(null);
    setSavedReceiptUrl(null);
    setUpdatedBalanceNotice(null);

    try {
      const res = await fetch('/api/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ text: inputText.trim() }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Could not parse text');
      }

      const draftData: DraftData = await res.json();
      setDraft(draftData);
    } catch (err: any) {
      setParseError(err.message || 'Pipeline parsing failed. You can create an entry manually.');
    } finally {
      setIsParsing(false);
    }
  };

  // Line item edits inside Confirm Card
  const updateDraftLine = (index: number, field: 'qty' | 'unitPrice' | 'name', value: any) => {
    if (!draft) return;
    const newLines = [...draft.lines];
    const target = { ...newLines[index], [field]: value };
    target.lineTotal = Math.max(0, (parseInt(target.qty as any) || 0) * (parseInt(target.unitPrice as any) || 0));
    newLines[index] = target;

    const newComputedTotal = newLines.reduce((acc, l) => acc + l.lineTotal, 0);
    const newTotal = draft.statedTotal !== null && draft.statedTotal !== undefined ? draft.statedTotal : newComputedTotal;
    const newDue = newTotal - draft.paid;

    // Check if error issues are now resolved
    const remainingIssues = draft.issues.filter(
      (i) => !i.field.startsWith(`lines[${index}]`)
    );

    setDraft({
      ...draft,
      lines: newLines,
      computedTotal: newComputedTotal,
      total: newTotal,
      due: newDue,
      issues: remainingIssues,
      canSave: !remainingIssues.some((i) => i.severity === 'error') && newLines.length > 0,
    });
  };

  const removeDraftLine = (index: number) => {
    if (!draft) return;
    const newLines = draft.lines.filter((_, i) => i !== index);
    const newComputedTotal = newLines.reduce((acc, l) => acc + l.lineTotal, 0);
    const newTotal = newComputedTotal;
    const newDue = newTotal - draft.paid;

    setDraft({
      ...draft,
      lines: newLines,
      computedTotal: newComputedTotal,
      total: newTotal,
      due: newDue,
      canSave: newLines.length > 0 && !!draft.customer?.name,
    });
  };

  const addDraftLine = () => {
    if (!draft) return;
    const newLine: DraftLine = {
      name: 'Custom Item',
      qty: 1,
      unitPrice: 500,
      lineTotal: 500,
      isAssumedPrice: false,
    };
    const newLines = [...draft.lines, newLine];
    const newComputedTotal = newLines.reduce((acc, l) => acc + l.lineTotal, 0);
    const newTotal = newComputedTotal;
    const newDue = newTotal - draft.paid;

    setDraft({
      ...draft,
      lines: newLines,
      computedTotal: newComputedTotal,
      total: newTotal,
      due: newDue,
      canSave: !!draft.customer?.name,
    });
  };

  const updatePaid = (val: number) => {
    if (!draft) return;
    const newPaid = Math.max(0, val);
    const newDue = draft.total - newPaid;
    setDraft({
      ...draft,
      paid: newPaid,
      due: newDue,
    });
  };

  // POST /api/entries (Save Entry)
  const handleSaveEntry = async () => {
    if (!draft || !draft.canSave) return;
    setIsSaving(true);

    try {
      const payload = {
        draftId: draft.draftId,
        customer: {
          id: draft.customer?.id || null,
          name: draft.customer?.name || 'Customer',
          isNew: draft.customer?.isNew || false,
          phone: draft.customer?.phone || null,
        },
        lines: draft.lines.map((l) => ({
          itemId: l.itemId || null,
          name: l.name,
          qty: l.qty,
          unitPrice: l.unitPrice,
        })),
        paid: draft.paid,
      };

      const res = await fetch('/api/entries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to save entry');
      }

      const data = await res.json();
      setSavedReceiptUrl(data.waReceiptUrl);
      setUpdatedBalanceNotice(
        `Entry saved! ${data.customerName}'s total balance is now ₹${data.customerUpdatedBalance.toLocaleString()}.`
      );
      setDraft(null); // Clear draft
      await loadWorkspaceData();
    } catch (err: any) {
      alert(err.message || 'Error saving entry');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-cream text-navy flex flex-col font-body selection:bg-turmeric selection:text-navy">
      {/* Top Bar with Wispr tip */}
      <header className="bg-cream-paper border-b border-navy/10 px-4 sm:px-6 py-4 sticky top-0 z-30 shadow-sm">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-navy/70 hover:text-navy px-2.5 py-1.5 rounded-lg bg-navy/5"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Landing</span>
            </Link>
            <div className="flex items-baseline gap-2">
              <span className="font-display font-extrabold text-2xl text-navy tracking-tight">BolKhata</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-turmeric text-navy">PHASE 1</span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs bg-turmeric/20 border border-turmeric/50 text-navy px-3 py-1.5 rounded-xl font-medium">
            <Mic className="w-3.5 h-3.5 text-navy" />
            <span>Tip: Click the box, hold your Wispr key and speak your sale.</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-8 w-full space-y-6">
        
        {/* Judge-Friendly Demo Banner */}
        <div className="p-3.5 rounded-2xl bg-amber-500/10 border-2 border-amber-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-navy shadow-sm">
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-4 h-4 text-turmeric-hover flex-shrink-0 animate-pulse" />
            <span className="font-semibold">
              <strong className="text-navy font-bold">Judge-Friendly Demo:</strong> Demo with sample data. Click an example, hit Read it, then try Fix it and Ask.
            </span>
          </div>
          <button
            onClick={initSession}
            disabled={sessionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-navy text-turmeric hover:bg-navy-light text-xs font-bold transition-all shadow-sm active:scale-95 whitespace-nowrap self-end sm:self-auto"
            title="Wipe current workspace and seed fresh demo data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${sessionLoading ? 'animate-spin' : ''}`} />
            <span>Reset Demo Data</span>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-navy/15 gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => setActiveTab('entry')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap ${
              activeTab === 'entry' ? 'bg-navy text-turmeric shadow-sm' : 'text-navy/70 hover:bg-navy/5'
            }`}
          >
            <Mic className="w-4 h-4" />
            <span>Record Sale</span>
          </button>

          <button
            onClick={() => { setActiveTab('ledger'); loadWorkspaceData(); }}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap ${
              activeTab === 'ledger' ? 'bg-navy text-turmeric shadow-sm' : 'text-navy/70 hover:bg-navy/5'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Ledger Entries ({ledger.length})</span>
          </button>

          <button
            onClick={() => { setActiveTab('customers'); loadWorkspaceData(); }}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap ${
              activeTab === 'customers' ? 'bg-navy text-turmeric shadow-sm' : 'text-navy/70 hover:bg-navy/5'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Customers ({customers.length})</span>
          </button>

          <button
            onClick={() => { setActiveTab('stock'); loadWorkspaceData(); }}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap ${
              activeTab === 'stock' ? 'bg-navy text-turmeric shadow-sm' : 'text-navy/70 hover:bg-navy/5'
            }`}
          >
            <Boxes className="w-4 h-4" />
            <span>Stock Inventory ({items.length})</span>
          </button>

          <button
            onClick={() => { setActiveTab('ask'); loadWorkspaceData(); }}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap ${
              activeTab === 'ask' ? 'bg-navy text-turmeric shadow-sm' : 'text-navy/70 hover:bg-navy/5'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Ask Ledger</span>
          </button>
        </div>

        {/* TAB 1: RECORD SALE (Entry + Confirm Card) */}
        {activeTab === 'entry' && (
          <div className="space-y-6">

            {/* Feature 6: Daily Summary Card ("Aaj Ka Hisaab") */}
            <div className="p-5 sm:p-6 rounded-3xl bg-navy text-cream border-2 border-navy shadow-paper space-y-4">
              <div className="flex items-center justify-between border-b border-cream/15 pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-turmeric animate-pulse" />
                  <div>
                    <h3 className="font-display font-extrabold text-lg text-cream">
                      Aaj Ka Hisaab (Daily Summary)
                    </h3>
                    <span className="text-[11px] text-cream/70 font-mono">
                      {dailySummary?.date || 'Asia/Kolkata'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={loadDailySummary}
                  className="p-2 rounded-xl bg-navy-light hover:bg-cream/10 text-turmeric text-xs font-semibold flex items-center gap-1.5 border border-cream/10 active:scale-95 transition-all"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isSummaryLoading ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>

              {dailySummary && (
                <>
                  {/* Summary Metric Stats */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                    <div className="p-3 rounded-2xl bg-navy-light/60 border border-cream/10">
                      <span className="text-[10px] uppercase font-bold text-cream/60 block">Entries</span>
                      <span className="text-xl font-display font-extrabold text-cream">
                        {dailySummary.entriesCount}
                      </span>
                    </div>
                    <div className="p-3 rounded-2xl bg-navy-light/60 border border-cream/10">
                      <span className="text-[10px] uppercase font-bold text-cream/60 block">Total Bikri</span>
                      <span className="text-xl font-display font-extrabold text-turmeric">
                        ₹{dailySummary.totalSales.toLocaleString()}
                      </span>
                    </div>
                    <div className="p-3 rounded-2xl bg-navy-light/60 border border-cream/10">
                      <span className="text-[10px] uppercase font-bold text-cream/60 block">Cash Mila</span>
                      <span className="text-xl font-display font-extrabold text-khataGreen">
                        ₹{dailySummary.cashCollected.toLocaleString()}
                      </span>
                    </div>
                    <div className="p-3 rounded-2xl bg-navy-light/60 border border-cream/10">
                      <span className="text-[10px] uppercase font-bold text-cream/60 block">Udhaar Diya</span>
                      <span className="text-xl font-display font-extrabold text-khataRed">
                        ₹{dailySummary.totalUdhaarGiven.toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {/* Narrative Sentence */}
                  <div className="p-3.5 rounded-2xl bg-cream/5 border border-cream/10 flex items-start gap-2.5">
                    <Info className="w-4 h-4 text-turmeric flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-cream/90 font-medium leading-relaxed">
                      {dailySummary.narrative}
                    </p>
                  </div>
                </>
              )}
            </div>
            
            {/* SaleEntry Component */}
            <div className="p-6 rounded-3xl bg-cream-paper border-2 border-navy/15 shadow-paper space-y-4">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-navy/70">
                    Dictated Sale Input (Roman Hinglish, Devanagari, or English)
                  </label>
                  <span className="text-[11px] text-navy/50 font-medium">Click an example to load:</span>
                </div>

                {/* 5 Clickable Demo Examples for Judges */}
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {[
                    {
                      label: "Standard Sale",
                      text: "Sharma ji ko do shirt aur ek trouser diye, 4200 bill, 2000 abhi diya, baaki udhaar",
                      badge: "Standard",
                      desc: "Complete sale with partial cash"
                    },
                    {
                      label: "Self-Correction",
                      text: "Gupta ji ko do shirt nahi teen shirt aur ek jeans diya, total 4500",
                      badge: "Fix it",
                      desc: "Contains 'nahi' correction word"
                    },
                    {
                      label: "Ambiguous Name",
                      text: "Sharma ko ek kurta aur pajama diya, 1800 jama kiya",
                      badge: "Ambiguous",
                      desc: "Sharma ji vs Sharma Sir prompt"
                    },
                    {
                      label: "Missing Customer",
                      text: "Do jeans aur ek formal shirt diye, 2500 total, 1000 cash",
                      badge: "Prompt Chip",
                      desc: "Triggers Missing Customer chips"
                    },
                    {
                      label: "Devanagari Hindi",
                      text: "वर्मा जी को दो पैंट और एक टी-शर्ट दी, 2000 बिल, 500 नकद",
                      badge: "Hindi Script",
                      desc: "Devanagari phonetics test"
                    }
                  ].map((ex, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setInputText(ex.text)}
                      className="px-2.5 py-1.5 rounded-xl bg-navy/5 hover:bg-turmeric/20 text-navy border border-navy/10 hover:border-turmeric text-left text-xs transition-all active:scale-95 group shadow-2xs flex items-center gap-1.5"
                      title={ex.desc}
                    >
                      <span className="font-bold text-navy group-hover:text-turmeric-hover">{ex.label}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-navy/10 text-navy/70 font-mono">
                        {ex.badge}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                maxLength={500}
                rows={3}
                placeholder="Click here, speak with Wispr Flow or type your sale..."
                className="w-full p-4 rounded-2xl bg-cream border-2 border-navy/20 font-medium text-navy text-base leading-relaxed focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner resize-none"
              />

              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-navy/50">{inputText.length} / 500 characters</span>

                <button
                  onClick={handleParse}
                  disabled={isParsing || !inputText.trim()}
                  className="px-7 py-3 rounded-xl bg-navy hover:bg-navy-light disabled:opacity-50 text-turmeric font-extrabold text-sm flex items-center gap-2 shadow-paper hover:shadow-turmeric-glow transition-all active:scale-[0.98]"
                >
                  {isParsing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-turmeric" />
                      <span>Parsing with Agents...</span>
                    </>
                  ) : (
                    <>
                      <BookOpen className="w-4 h-4 text-turmeric" />
                      <span>Read it (Parse Entry)</span>
                    </>
                  )}
                </button>
              </div>

              {parseError && (
                <div className="p-3 rounded-xl bg-khataRed/10 border border-khataRed/30 text-khataRed text-xs font-semibold flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{parseError}</span>
                </div>
              )}
            </div>

            {/* Success Notice & WhatsApp Link */}
            {updatedBalanceNotice && (
              <div className="p-5 rounded-2xl bg-khataGreen/15 border-2 border-khataGreen/40 text-navy space-y-3">
                <div className="flex items-center gap-2 text-khataGreen font-bold text-sm">
                  <CheckCircle2 className="w-5 h-5" />
                  <span>{updatedBalanceNotice}</span>
                </div>
                {savedReceiptUrl && (
                  <a
                    href={savedReceiptUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-khataGreen hover:bg-opacity-90 text-white font-bold text-sm shadow-sm transition-all active:scale-95"
                  >
                    <Send className="w-4 h-4" />
                    <span>Send receipt on WhatsApp</span>
                  </a>
                )}
              </div>
            )}

            {/* ConfirmCard Component */}
            {draft && (
              <div className="p-6 sm:p-8 rounded-3xl bg-navy text-cream border-2 border-navy shadow-paper-lg space-y-6">
                <div className="flex items-center justify-between border-b border-cream/15 pb-4">
                  <div className="space-y-0.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-turmeric">
                      Step 2: Confirm Entry
                    </span>
                    <h3 className="font-display font-extrabold text-xl text-cream">
                      Review & Commit to Bahi-Khata
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    {draft.modelInfo?.isFallback && (
                      <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 shadow-sm animate-pulse">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                        Offline mode: check carefully
                      </span>
                    )}
                    {draft.modelInfo?.cached && (
                      <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                        ⚡ Instant Warm Cache
                      </span>
                    )}
                    {!draft.modelInfo?.isFallback && draft.modelInfo?.model && (
                      <span className="px-2.5 py-1 rounded-full text-[11px] font-mono bg-khataGreen/20 text-khataGreen border border-khataGreen/30">
                        {draft.modelInfo.model} ({draft.modelInfo.latencyMs ?? 0}ms)
                      </span>
                    )}
                    <span className="text-xs font-mono px-2.5 py-1 rounded bg-cream/10 text-cream/80">
                      Draft ID: {draft.draftId.slice(-6)}
                    </span>
                  </div>
                </div>

                {/* Issues and Targeted Missing-Field Prompts (Feature 3: No Model Call) */}
                {draft.issues.length > 0 && (
                  <div className="space-y-3">
                    {draft.issues.map((iss, i) => (
                      <div
                        key={i}
                        className={`p-3.5 rounded-2xl text-xs space-y-2.5 font-medium ${
                          iss.severity === 'error'
                            ? 'bg-khataRed/20 border border-khataRed/40 text-white'
                            : 'bg-turmeric/20 border border-turmeric/40 text-turmeric'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold uppercase tracking-wide mr-1">[{iss.severity}]:</span>
                            <span>{iss.message}</span>
                          </div>
                        </div>

                        {/* Targeted prompt chips for blocking issues */}
                        {(iss.code === 'MISSING_CUSTOMER' || iss.code === 'CUSTOMER_NOT_IN_TEXT') && (
                          <div className="pt-1 border-t border-white/10 space-y-1.5">
                            <span className="text-[11px] font-bold text-cream/90 flex items-center gap-1">
                              👉 Kis customer ko bill karna hai? (Tap to select):
                            </span>
                            <div className="flex flex-wrap items-center gap-1.5">
                              {customers.slice(0, 4).map((c) => (
                                <button
                                  key={c.id}
                                  type="button"
                                  onClick={() => handleDirectPatch([{ op: 'set_customer', customerId: c.id }])}
                                  className="px-2.5 py-1 rounded-lg bg-navy hover:bg-cream/20 text-cream text-[11px] font-semibold border border-cream/25 active:scale-95 transition-all shadow-sm"
                                >
                                  {c.name}
                                </button>
                              ))}
                              <button
                                type="button"
                                onClick={() => handleDirectPatch([{ op: 'set_customer', customerName: 'New Customer' }])}
                                className="px-2.5 py-1 rounded-lg bg-turmeric/20 hover:bg-turmeric/30 text-turmeric text-[11px] font-semibold border border-turmeric/40 active:scale-95 transition-all"
                              >
                                + Naya Customer
                              </button>
                            </div>
                          </div>
                        )}

                        {iss.code === 'MISSING_QUANTITY' && (
                          <div className="pt-1 border-t border-white/10 space-y-1.5">
                            <span className="text-[11px] font-bold text-cream/90 flex items-center gap-1">
                              👉 Kitni quantity chahiye? (Tap number):
                            </span>
                            <div className="flex flex-wrap items-center gap-1.5">
                              {(() => {
                                // Extract line index from field e.g. "lines[0].qty"
                                const match = iss.field.match(/lines\[(\d+)\]/);
                                const lIdx = match ? parseInt(match[1], 10) : 0;
                                return [1, 2, 3, 4, 5, 10].map((num) => (
                                  <button
                                    key={num}
                                    type="button"
                                    onClick={() => handleDirectPatch([{ op: 'set_line_qty', lineIndex: lIdx, qty: num }])}
                                    className="px-2.5 py-1 rounded-lg bg-navy hover:bg-cream/20 text-cream text-[11px] font-bold border border-cream/25 active:scale-95 transition-all shadow-sm"
                                  >
                                    {num}
                                  </button>
                                ));
                              })()}
                            </div>
                          </div>
                        )}

                        {(iss.code === 'NO_ITEMS' || iss.code === 'ITEM_NOT_IN_TEXT' || iss.code === 'UNKNOWN_ITEM') && (
                          <div className="pt-1 border-t border-white/10 space-y-1.5">
                            <span className="text-[11px] font-bold text-cream/90 flex items-center gap-1">
                              👉 Kaun sa item jodna hai? (Catalog se chuniye):
                            </span>
                            <div className="flex flex-wrap items-center gap-1.5">
                              {items.slice(0, 4).map((it) => (
                                <button
                                  key={it.id}
                                  type="button"
                                  onClick={() => handleDirectPatch([{ op: 'add_line', itemId: it.id, qty: 1 }])}
                                  className="px-2.5 py-1 rounded-lg bg-navy hover:bg-cream/20 text-cream text-[11px] font-semibold border border-cream/25 active:scale-95 transition-all shadow-sm"
                                >
                                  + {it.name} (₹{it.price})
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Customer Selector / Name Input */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-cream/70">
                      Customer (ग्राहक)
                    </label>
                    <select
                      value={draft.customer?.id || 'new'}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === 'new') {
                          setDraft({
                            ...draft,
                            customer: { id: null, name: 'New Customer', isNew: true },
                            canSave: true,
                          });
                        } else {
                          const found = customers.find((c) => c.id === val);
                          if (found) {
                            setDraft({
                              ...draft,
                              customer: { id: found.id, name: found.name, phone: found.phone, isNew: false },
                              canSave: true,
                            });
                          }
                        }
                      }}
                      className="w-full p-3 rounded-xl bg-navy-light border border-cream/20 text-cream text-sm focus:outline-none focus:ring-2 focus:ring-turmeric"
                    >
                      {customers.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} {c.balance > 0 ? `(Udhaar: ₹${c.balance})` : ''}
                        </option>
                      ))}
                      <option value="new">+ Add New Customer</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-cream/70">
                      Customer Name
                    </label>
                    <input
                      type="text"
                      value={draft.customer?.name || ''}
                      onChange={async (e) => {
                        const newName = e.target.value;
                        setDraft({
                          ...draft,
                          customer: { ...draft.customer, name: newName, isNew: !draft.customer?.id },
                          canSave: !!newName.trim() && draft.lines.length > 0,
                        });
                        if (newName.trim().length >= 3) {
                          try {
                            const res = await fetch('/api/customers/match-fuzzy', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              credentials: 'include',
                              body: JSON.stringify({ name: newName }),
                            });
                            if (res.ok) {
                              const matchData = await res.json();
                              setFuzzyWarning(matchData.nearDuplicateWarning || null);
                              if (matchData.decision === 'ASK_USER' || matchData.nearDuplicateWarning) {
                                setFuzzyCandidates(matchData.candidates || []);
                              } else {
                                setFuzzyCandidates([]);
                              }
                            }
                          } catch (err) {
                            console.error('Fuzzy check error:', err);
                          }
                        } else {
                          setFuzzyWarning(null);
                          setFuzzyCandidates([]);
                        }
                      }}
                      placeholder="e.g. Sharma ji"
                      className="w-full p-3 rounded-xl bg-navy-light border border-cream/20 text-cream text-sm focus:outline-none focus:ring-2 focus:ring-turmeric"
                    />

                    {/* Near duplicate warning and candidate chips (Feature 4) */}
                    {fuzzyWarning && (
                      <div className="p-2.5 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-200 text-xs space-y-1.5 animate-fadeIn">
                        <div className="flex items-center gap-1.5 font-bold">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                          <span>{fuzzyWarning}</span>
                        </div>
                        {fuzzyCandidates.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 pt-1">
                            {fuzzyCandidates.map((c) => (
                              <button
                                key={c.id}
                                type="button"
                                onClick={async () => {
                                  // Set customer match and add spoken name as alias
                                  const spoken = draft.customer?.name || '';
                                  setDraft({
                                    ...draft,
                                    customer: { id: c.id, name: c.name, phone: c.phone, isNew: false },
                                    canSave: true,
                                  });
                                  setFuzzyWarning(null);
                                  setFuzzyCandidates([]);
                                  if (spoken && spoken.toLowerCase() !== c.name.toLowerCase()) {
                                    try {
                                      await fetch(`/api/customers/${c.id}/aliases`, {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        credentials: 'include',
                                        body: JSON.stringify({ alias: spoken }),
                                      });
                                    } catch (e) {
                                      console.error('Failed to register alias:', e);
                                    }
                                  }
                                }}
                                className="px-2.5 py-1 rounded-lg bg-navy hover:bg-cream/20 text-cream text-[11px] font-semibold border border-cream/30 active:scale-95 transition-all shadow-sm"
                              >
                                Match "{c.name}"
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Line Items Table */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-cream/70 border-b border-cream/10 pb-2">
                    <span>Line Items</span>
                    <button
                      type="button"
                      onClick={addDraftLine}
                      className="inline-flex items-center gap-1 text-xs text-turmeric font-bold hover:underline"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add Item
                    </button>
                  </div>

                  <div className="space-y-2">
                    {draft.lines.map((line, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 text-sm ${
                          line.isAssumedPrice ? 'bg-turmeric/10 border-turmeric/40' : 'bg-navy-light border-cream/10'
                        }`}
                      >
                        <div className="flex-1 space-y-1">
                          <input
                            type="text"
                            value={line.name}
                            onChange={(e) => updateDraftLine(idx, 'name', e.target.value)}
                            className="w-full bg-transparent font-semibold text-cream border-b border-cream/20 focus:outline-none"
                          />
                          {line.isAssumedPrice && (
                            <span className="text-[10px] text-turmeric font-mono block">
                              * Price assumed from catalog
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-1">
                            <span className="text-xs text-cream/60">Qty:</span>
                            <input
                              type="number"
                              min={1}
                              max={1000}
                              value={line.qty}
                              onChange={(e) => updateDraftLine(idx, 'qty', parseInt(e.target.value) || 1)}
                              className="w-16 p-1.5 rounded-lg bg-navy border border-cream/20 text-cream text-center text-sm"
                            />
                          </div>

                          <div className="flex items-center gap-1">
                            <span className="text-xs text-cream/60">₹:</span>
                            <input
                              type="number"
                              min={0}
                              value={line.unitPrice}
                              onChange={(e) => updateDraftLine(idx, 'unitPrice', parseInt(e.target.value) || 0)}
                              className="w-24 p-1.5 rounded-lg bg-navy border border-cream/20 text-cream text-right text-sm"
                            />
                          </div>

                          <div className="w-24 text-right font-display font-bold text-turmeric">
                            ₹{line.lineTotal.toLocaleString()}
                          </div>

                          <button
                            type="button"
                            onClick={() => removeDraftLine(idx)}
                            className="p-1 text-cream/40 hover:text-khataRed transition-colors"
                            title="Remove line"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Self-Correction Audit Banner (When user used nahi, matlab, sorry, actually) */}
                  {(() => {
                    const text = draft.rawText?.toLowerCase() || '';
                    const match = text.match(/\b(nahi|nahi nahi|matlab|sorry|actually)\b/i);
                    if (!match) return null;
                    const triggerWord = match[0].toLowerCase();
                    return (
                      <div className="p-3.5 rounded-2xl bg-turmeric/10 border border-turmeric/30 space-y-2 text-xs">
                        <div className="flex items-center gap-2 text-turmeric font-bold">
                          <History className="w-4 h-4 flex-shrink-0" />
                          <span>Voice Self-Correction Detected ("{triggerWord}")</span>
                        </div>
                        <p className="text-cream/80 text-[11px] leading-relaxed">
                          The counter voice input contained a retraction / self-correction. Earlier spoken items or values were replaced:
                        </p>
                        <div className="flex flex-wrap gap-2 pt-1">
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-khataRed/20 border border-khataRed/40 text-cream/70 line-through text-[11px]">
                            <Undo2 className="w-3 h-3 text-khataRed" />
                            Retracted earlier item / value
                          </span>
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-khataGreen/20 border border-khataGreen/40 text-khataGreen font-semibold text-[11px]">
                            ✓ Kept replacement in final bill
                          </span>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* Financial Summary & Paid Input (with List Price and Discount breakdown) */}
                <div className="pt-4 border-t border-cream/15 grid grid-cols-1 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 rounded-xl bg-navy-light border border-cream/10 text-center">
                    <span className="text-[11px] text-cream/60 uppercase font-bold block mb-0.5">List Price (MRP)</span>
                    <span className="text-xl font-bold font-display text-cream/90">
                      ₹{(draft.listPrice ?? draft.computedTotal).toLocaleString()}
                    </span>
                    <span className="text-[10px] text-cream/50 block">sum of lines</span>
                  </div>

                  <div className={`p-3.5 rounded-xl border text-center ${
                    (draft.discount ?? 0) > 0
                      ? 'bg-turmeric/10 border-turmeric/30 text-turmeric'
                      : 'bg-navy-light border-cream/10 text-cream/70'
                  }`}>
                    <span className="text-[11px] uppercase font-bold block mb-0.5">
                      {(draft.discount ?? 0) >= 0 ? 'Discount' : 'Surcharge'}
                    </span>
                    <span className="text-xl font-bold font-display">
                      {(draft.discount ?? 0) >= 0
                        ? `₹${(draft.discount ?? 0).toLocaleString()}`
                        : `+₹${Math.abs(draft.discount ?? 0).toLocaleString()}`}
                    </span>
                    <span className="text-[10px] opacity-75 block">
                      {(draft.discount ?? 0) > 0 && (draft.listPrice ?? draft.computedTotal) > 0
                        ? `${Math.round((draft.discount ?? 0) / (draft.listPrice ?? draft.computedTotal) * 100)}% off list`
                        : 'stated bill diff'}
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-navy-light border border-turmeric/40 text-center">
                    <span className="text-[11px] text-turmeric uppercase font-bold block mb-0.5">Total Bill (Stated)</span>
                    <span className="text-2xl font-extrabold font-display text-turmeric">
                      ₹{draft.total.toLocaleString()}
                    </span>
                    <span className="text-[10px] text-turmeric/80 block">final customer bill</span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-khataGreen/15 border border-khataGreen/30 text-center space-y-1">
                    <span className="text-[11px] text-khataGreen uppercase font-bold block">Paid (Jama)</span>
                    <input
                      type="number"
                      min={0}
                      value={draft.paid}
                      onChange={(e) => updatePaid(parseInt(e.target.value) || 0)}
                      className="w-full p-1.5 rounded-lg bg-navy border border-khataGreen/40 text-center text-lg font-extrabold text-khataGreen font-display"
                    />
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-khataRed/10 border border-khataRed/30 flex items-center justify-between text-sm">
                  <span className="text-khataRed font-semibold">Baaki Udhaar (Due Balance):</span>
                  <span className="text-xl font-extrabold font-display text-khataRed">
                    ₹{draft.due.toLocaleString()}
                  </span>
                </div>

                {/* Save Button */}
                <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <span className="text-xs text-cream/60">
                    {draft.canSave
                      ? '✓ All required fields verified. Ready to save.'
                      : 'Fix blocking issues above (customer or quantity) to save.'}
                  </span>

                  <button
                    onClick={handleSaveEntry}
                    disabled={isSaving || !draft.canSave}
                    className="w-full sm:w-auto px-8 py-4 rounded-xl bg-turmeric hover:bg-turmeric-hover disabled:opacity-50 text-navy font-extrabold text-base flex items-center justify-center gap-2 shadow-paper-lg transition-all"
                  >
                    {isSaving ? (
                      <>
                        <RefreshCw className="w-5 h-5 animate-spin text-navy" />
                        <span>Saving to Ledger...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-5 h-5 text-navy" />
                        <span>Save entry to Bahi-Khata</span>
                      </>
                    )}
                  </button>
                </div>

                {/* FEATURE 1: FIX IT / CORRECTION BY VOICE */}
                <div className="mt-4 pt-4 border-t border-cream/15 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-turmeric flex items-center gap-1.5">
                      <Mic className="w-3.5 h-3.5" />
                      Fix it by voice / follow-up ({correctionCount}/5 used)
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCorrection("nahi, total 4500")}
                      className="text-[11px] text-turmeric hover:underline"
                    >
                      Sample: "nahi, total 4500"
                    </button>
                  </div>

                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={correctionText}
                      maxLength={300}
                      onChange={(e) => setCorrectionText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCorrection();
                      }}
                      placeholder='e.g. "nahi, total 4500", "do nahi teen shirt", "Sharma Sir ko likho"'
                      className="flex-1 p-3 rounded-xl bg-navy-light border border-cream/20 text-cream text-xs focus:outline-none focus:ring-2 focus:ring-turmeric placeholder:text-cream/40"
                    />
                    <button
                      type="button"
                      onClick={() => handleCorrection()}
                      disabled={isCorrecting || !correctionText.trim()}
                      className="px-4 py-2.5 rounded-xl bg-turmeric hover:bg-turmeric-hover disabled:opacity-50 text-navy font-bold text-xs flex items-center gap-1.5"
                    >
                      {isCorrecting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Fix it'}
                    </button>
                  </div>

                  {/* Clarifying Question with tap options */}
                  {clarifyingQuestion && (
                    <div className="p-3.5 rounded-xl bg-turmeric/15 border border-turmeric/40 space-y-2">
                      <p className="text-xs font-bold text-turmeric">
                        {clarifyingQuestion.question}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {clarifyingQuestion.options.map((opt, oIdx) => (
                          <button
                            key={oIdx}
                            type="button"
                            onClick={() => {
                              if (opt.toLowerCase() === 'cancel') {
                                setClarifyingQuestion(null);
                              } else {
                                handleCorrection(opt);
                              }
                            }}
                            className="px-3 py-1.5 rounded-lg bg-navy text-turmeric font-semibold text-xs border border-turmeric/30 hover:bg-navy-light"
                          >
                            {opt}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Correction Diffs */}
                  {correctionDiffs.length > 0 && (
                    <div className="p-3 rounded-xl bg-cream/5 border border-cream/10 space-y-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-cream/60 block">
                        Recent Changes Applied:
                      </span>
                      {correctionDiffs.map((d, dIdx) => (
                        <div key={dIdx} className="text-xs font-mono flex items-center gap-2 text-cream/90">
                          <span className="font-bold text-turmeric">{d.field}:</span>
                          <span className="text-khataRed line-through">{String(d.before)}</span>
                          <span>&rarr;</span>
                          <span className="text-khataGreen font-bold">{String(d.after)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>
            )}

          </div>
        )}

        {/* TAB 2: LEDGER */}
        {activeTab === 'ledger' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-extrabold text-xl text-navy">
                Workspace Ledger History (Newest First)
              </h3>
              {ledger.length > 0 && (
                <button
                  type="button"
                  onClick={handleUndoLastEntry}
                  disabled={isUndoing}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-khataRed/10 hover:bg-khataRed/20 text-khataRed font-bold text-xs border border-khataRed/30 active:scale-95 transition-all shadow-2xs"
                  title="Undo only the most recent entry within 15 minutes"
                >
                  <Undo2 className={`w-3.5 h-3.5 ${isUndoing ? 'animate-spin' : ''}`} />
                  <span>Undo Last Entry</span>
                </button>
              )}
            </div>

            {undoNotice && (
              <div className="p-3.5 rounded-2xl bg-khataGreen/15 border border-khataGreen/40 text-navy text-xs font-bold flex items-center gap-2 animate-fadeIn">
                <CheckCircle2 className="w-4 h-4 text-khataGreen flex-shrink-0" />
                <span>{undoNotice}</span>
              </div>
            )}

            {ledger.length === 0 ? (
              <div className="p-8 rounded-2xl bg-cream-paper border-2 border-navy/10 text-center space-y-2">
                <p className="text-sm text-navy/70">No entries recorded in this workspace session yet.</p>
                <button
                  onClick={() => setActiveTab('entry')}
                  className="px-4 py-2 rounded-xl bg-navy text-turmeric font-bold text-xs"
                >
                  Record your first sale
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {ledger.map((entry) => (
                  <div
                    key={entry.id}
                    className="p-5 rounded-2xl bg-cream-paper border-2 border-navy/15 shadow-sm space-y-3"
                  >
                    <div className="flex items-center justify-between border-b border-navy/10 pb-2.5">
                      <div className="space-y-0.5">
                        <span className="font-display font-bold text-lg text-navy">{entry.customerName}</span>
                        <span className="text-xs text-navy/50 block font-mono">
                          {new Date(entry.createdAt).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <span className="px-2.5 py-1 rounded-full bg-khataGreen/15 text-khataGreen font-bold text-xs">
                          Paid: ₹{entry.paid.toLocaleString()}
                        </span>
                        <span className="px-2.5 py-1 rounded-full bg-khataRed/15 text-khataRed font-bold text-xs">
                          Due: ₹{entry.due.toLocaleString()}
                        </span>
                      </div>
                    </div>

                    {/* Lines */}
                    <div className="space-y-1 text-xs text-navy/80">
                      {entry.lines.map((l, idx) => (
                        <div key={idx} className="flex justify-between">
                          <span>{l.qty}x {l.name}</span>
                          <span className="font-mono">₹{l.lineTotal.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-navy/10 text-xs">
                      <span className="font-bold text-navy">Total Bill: ₹{entry.total.toLocaleString()}</span>
                      <a
                        href={`https://wa.me/?text=${encodeURIComponent(
                          `BolKhata Receipt for ${entry.customerName}:\nTotal: ₹${entry.total}\nPaid: ₹${entry.paid}\nDue: ₹${entry.due}`
                        )}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-khataGreen font-bold hover:underline flex items-center gap-1 active:scale-95"
                      >
                        <Send className="w-3.5 h-3.5" /> WhatsApp Receipt
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: CUSTOMERS */}
        {activeTab === 'customers' && (
          <div className="space-y-4">
            <h3 className="font-display font-extrabold text-xl text-navy">
              Customer Accounts (Sorted by Udhaar Due)
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {customers.map((c) => (
                <div
                  key={c.id}
                  className="p-5 rounded-2xl bg-cream-paper border-2 border-navy/15 shadow-sm flex items-center justify-between"
                >
                  <div className="space-y-1.5 flex-1 pr-4">
                    <span className="font-display font-bold text-base text-navy block">{c.name}</span>
                    
                    {/* Customer Phone Editing */}
                    {editingPhoneCustId === c.id ? (
                      <div className="flex items-center gap-1.5 pt-0.5">
                        <input
                          type="text"
                          value={phoneInputVal}
                          onChange={(e) => setPhoneInputVal(e.target.value)}
                          placeholder="e.g. 9874961805"
                          className="px-2 py-1 text-xs rounded-lg bg-cream border border-navy/30 text-navy font-mono w-32 focus:outline-none focus:ring-1 focus:ring-turmeric"
                          autoFocus
                        />
                        <button
                          type="button"
                          onClick={() => handleSavePhone(c.id)}
                          disabled={isSavingPhone || !phoneInputVal.trim()}
                          className="px-2 py-1 rounded-lg bg-khataGreen text-white text-[11px] font-bold active:scale-95 disabled:opacity-50"
                        >
                          {isSavingPhone ? '...' : 'Save'}
                        </button>
                        <button
                          type="button"
                          onClick={() => { setEditingPhoneCustId(null); setPhoneInputVal(''); }}
                          className="px-1.5 py-1 text-navy/50 text-[11px] hover:text-navy"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-navy/60 font-mono">
                          {c.phone || 'No phone recorded'}
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingPhoneCustId(c.id);
                            setPhoneInputVal(c.phone ? c.phone.replace(/[^0-9]/g, '') : '');
                          }}
                          className="text-[10px] text-turmeric-hover hover:underline font-bold"
                        >
                          {c.phone ? 'Edit' : '+ Add Phone'}
                        </button>
                      </div>
                    )}

                    {c.balance > 0 && (
                      <button
                        type="button"
                        onClick={() => fetchReminder(c, 'polite')}
                        className="inline-flex items-center gap-1.5 px-3 py-1 mt-1 rounded-xl bg-turmeric/20 hover:bg-turmeric/30 text-navy font-bold text-xs border border-turmeric/50 active:scale-95 transition-all shadow-sm"
                      >
                        <Send className="w-3.5 h-3.5 text-turmeric" />
                        <span>Remind</span>
                      </button>
                    )}
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-navy/50 block">Udhaar Balance</span>
                    <span
                      className={`text-lg font-display font-extrabold ${
                        c.balance > 0 ? 'text-khataRed' : 'text-khataGreen'
                      }`}
                    >
                      ₹{c.balance.toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Feature 5: Reminder Draft Preview Modal */}
            {reminderModal && (
              <div className="fixed inset-0 z-50 bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4">
                <div className="w-full max-w-md p-6 rounded-3xl bg-navy text-cream border-2 border-cream/20 shadow-2xl space-y-4 animate-scaleUp">
                  <div className="flex items-center justify-between border-b border-cream/15 pb-3">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-turmeric">
                        Payment Reminder Draft
                      </span>
                      <h4 className="font-display font-bold text-lg text-cream">
                        {reminderModal.customer.name} (Due: ₹{reminderModal.customer.balance})
                      </h4>
                    </div>
                    <button
                      type="button"
                      onClick={() => setReminderModal(null)}
                      className="p-1.5 rounded-lg hover:bg-cream/10 text-cream/70 hover:text-cream"
                    >
                      ✕
                    </button>
                  </div>

                  {/* Tone Toggle */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-cream/70 font-semibold">Tone:</span>
                    <button
                      type="button"
                      onClick={() => fetchReminder(reminderModal.customer, 'polite')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                        reminderModal.tone === 'polite'
                          ? 'bg-khataGreen text-white shadow-sm'
                          : 'bg-navy-light text-cream/60 hover:text-cream'
                      }`}
                    >
                      Polite (विनम्र)
                    </button>
                    <button
                      type="button"
                      onClick={() => fetchReminder(reminderModal.customer, 'firm')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                        reminderModal.tone === 'firm'
                          ? 'bg-turmeric text-navy font-extrabold shadow-sm'
                          : 'bg-navy-light text-cream/60 hover:text-cream'
                      }`}
                    >
                      Firm (सख्त)
                    </button>
                  </div>

                  {/* Message Preview */}
                  <div className="p-3.5 rounded-xl bg-navy-light border border-cream/15 font-mono text-xs whitespace-pre-wrap leading-relaxed text-cream/90 min-h-[120px]">
                    {reminderModal.loading ? 'Generating reminder draft...' : reminderModal.text}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setReminderModal(null)}
                      className="px-4 py-2 rounded-xl text-xs font-bold text-cream/70 hover:bg-cream/10"
                    >
                      Cancel
                    </button>
                    {reminderModal.waUrl && (
                      <a
                        href={reminderModal.waUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-khataGreen hover:bg-opacity-90 text-white font-bold text-xs shadow-md transition-all active:scale-95"
                      >
                        <Send className="w-4 h-4" />
                        <span>Open WhatsApp</span>
                      </a>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: STOCK INVENTORY */}
        {activeTab === 'stock' && (
          <div className="space-y-4">
            <h3 className="font-display font-extrabold text-xl text-navy">
              Current Inventory Stock
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {items.map((it) => (
                <div
                  key={it.id}
                  className="p-4 rounded-2xl bg-cream-paper border-2 border-navy/15 shadow-sm space-y-2"
                >
                  <div className="flex justify-between items-start">
                    <span className="font-display font-bold text-base text-navy">{it.name}</span>
                    <span className="font-mono text-xs font-bold text-navy/70">₹{it.price}</span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-navy/10 text-xs">
                    <span className="text-navy/60">Available:</span>
                    <span
                      className={`font-bold px-2 py-0.5 rounded ${
                        it.stock < 15 ? 'bg-khataRed/15 text-khataRed' : 'bg-khataGreen/15 text-khataGreen'
                      }`}
                    >
                      {it.stock} units {it.stock < 15 && '(Low)'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: ASK YOUR LEDGER */}
        {activeTab === 'ask' && (
          <div className="space-y-6">
            <div className="p-6 rounded-3xl bg-cream-paper border-2 border-navy/15 shadow-paper space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-display font-extrabold text-xl text-navy flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-turmeric" />
                    Ask Your Ledger
                  </h3>
                  <p className="text-xs text-navy/70">
                    Ask questions in natural Hinglish or English about balances, sales, dues, or inventory stock.
                  </p>
                </div>
              </div>

              {/* Example Question Chips */}
              <div className="flex flex-wrap gap-2 pt-1">
                {[
                  "Sharma ji ka kitna baaki hai?",
                  "sabse zyada udhaar kiska hai?",
                  "aaj kitni bikri hui?",
                  "shirt kitni bachi hai?",
                  "Verma ji ka last bill kab tha?"
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setAskQuestion(chip);
                      handleAsk(chip);
                    }}
                    className="px-3 py-1.5 rounded-full bg-cream border border-navy/20 hover:border-turmeric text-xs font-semibold text-navy/80 transition-all"
                  >
                    "{chip}"
                  </button>
                ))}
              </div>

              {/* Input & Ask button */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={askQuestion}
                  maxLength={300}
                  onChange={(e) => setAskQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAsk();
                  }}
                  placeholder="Ask a question about your accounts, stock, or sales..."
                  className="flex-1 p-3.5 rounded-2xl bg-cream border-2 border-navy/20 text-navy text-sm font-medium focus:outline-none focus:ring-2 focus:ring-turmeric shadow-inner"
                />
                <button
                  type="button"
                  onClick={() => handleAsk()}
                  disabled={isAsking || !askQuestion.trim()}
                  className="px-6 py-3 rounded-2xl bg-navy hover:bg-navy-light disabled:opacity-50 text-turmeric font-extrabold text-sm flex items-center gap-2 shadow-sm"
                >
                  {isAsking ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Ask'}
                </button>
              </div>
            </div>

            {/* Answer & Verifiable Facts Card */}
            {askResult && (
              <div className="p-6 rounded-3xl bg-navy text-cream border-2 border-navy shadow-paper-lg space-y-4">
                <div className="flex items-center justify-between border-b border-cream/15 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-turmeric">
                      Ledger Answer
                    </span>
                    {askResult.sourceBadge && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cream/10 text-cream/70 border border-cream/20">
                        {askResult.sourceBadge}
                      </span>
                    )}
                  </div>
                </div>

                {/* Candidate choices if ambiguous */}
                {askResult.isAmbiguous && askResult.candidates && (
                  <div className="p-4 rounded-2xl bg-turmeric/15 border border-turmeric/40 space-y-2">
                    <p className="text-xs font-bold text-turmeric">
                      {askResult.clarificationQuestion || "Multiple matches found. Choose one:"}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {askResult.candidates.map((cand, cIdx) => (
                        <button
                          key={cIdx}
                          type="button"
                          onClick={() => {
                            const newQ = `${cand} ka kitna baaki hai?`;
                            setAskQuestion(newQ);
                            handleAsk(newQ);
                          }}
                          className="px-3.5 py-1.5 rounded-xl bg-navy text-turmeric font-bold text-xs border border-turmeric/30 hover:bg-navy-light"
                        >
                          {cand}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Answer Sentence */}
                <p className="text-lg font-medium text-cream leading-relaxed">
                  {askResult.answer}
                </p>

                {/* Verifiable Facts Card */}
                {askResult.facts && Object.keys(askResult.facts).length > 0 && (
                  <div className="p-4 rounded-2xl bg-navy-light border border-cream/15 space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-turmeric block">
                      Verifiable Ledger Facts (Computed in Python)
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono">
                      {Object.entries(askResult.facts).map(([k, v], fIdx) => (
                        <div key={fIdx} className="p-2 rounded-lg bg-navy/60 border border-cream/10">
                          <span className="text-cream/50 block text-[10px] uppercase">{k}</span>
                          <span className="text-cream font-bold text-sm">
                            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
};
