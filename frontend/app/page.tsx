"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Mail, Sparkles, AlertOctagon, HelpCircle, EyeOff, CheckCircle, 
  Send, User, Clock, ShieldAlert, Award, Calendar, ChevronRight, 
  Search, ShieldCheck, RefreshCw, Cpu, Activity, Database, Check, PlayCircle
} from "lucide-react";
import { SimulatorPanel } from "../components/SimulatorPanel";

const API_BASE = "http://127.0.0.1:8000";

interface Message {
  id: string;
  category: string;
  note: string;
  input: {
    message: {
      channel: string;
      from: string;
      body: string;
    };
    patient_id: string | null;
    now: string;
  };
  expected_outcome: string;
  queue_type?: string;
}

interface Proposal {
  provider_id: string;
  provider_name: string;
  service_id: string;
  service_name: string;
  start_time: string;
  duration_minutes: number;
  price_usd: number;
  rescheduled_appointment_id?: string | null;
}

interface DecideResponse {
  outcome: string;
  booking_proposal?: Proposal | null;
  rationale?: string | null;
  question?: string | null;
  reason?: string | null;
  alternative_proposals?: Proposal[] | null;
  confidence_score?: number | null;
  violated_rules?: string[] | null;
  decision_stages?: string[] | null;
  event_stream?: {
    stage_name: string;
    status: string;
    duration_ms: number;
    started_at: number;
    finished_at?: number | null;
    metadata?: any;
  }[] | null;
  metadata?: {
    latency_ms: number;
    model: string;
    api_provider: string;
    timestamp: string;
    prompt_tokens?: number;
    completion_tokens?: number;
    estimated_cost_usd?: number;
    fallback_used?: boolean;
    retries?: number;
  } | null;
}

interface CRMData {
  patients: any[];
  providers: any[];
  services: any[];
  appointments: any[];
}

export default function Dashboard() {
  // Database & Queues state
  const [allMessages, setAllMessages] = useState<Message[]>([]);
  const [completedList, setCompletedList] = useState<Record<string, { proposal: Proposal; override_reason?: string }>>({});
  const [archivedList, setArchivedList] = useState<Record<string, boolean>>({});
  
  const [activeQueue, setActiveQueue] = useState<string>("simulation");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCase, setSelectedCase] = useState<Message | null>(null);
  
  // Decided state (AI outcome)
  const [isDeciding, setIsDeciding] = useState<boolean>(false);
  const [decideResult, setDecideResult] = useState<DecideResponse | null>(null);
  
  // Interactive / Override States
  const [editedProviderId, setEditedProviderId] = useState<string>("");
  const [editedStartTime, setEditedStartTime] = useState<string>("");
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [composerText, setComposerText] = useState<string>("");
  
  // CRM & Database state
  const [crmData, setCrmData] = useState<CRMData | null>(null);
  const [selectedPatientProfile, setSelectedPatientProfile] = useState<any | null>(null);
  
  // Evals Harness state
  const [isRunningEvals, setIsRunningEvals] = useState<boolean>(false);
  const [evalsResult, setEvalsResult] = useState<any | null>(null);
  
  // UI Status Alerts
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [activeTabRight, setActiveTabRight] = useState<string>("decision"); // "decision" | "crm" | "calendar"
  
  // Staff AI Assistant state
  const [isAskAiOpen, setIsAskAiOpen] = useState<boolean>(false);
  const [askAiQuestion, setAskAiQuestion] = useState<string>("");
  const [askAiHistory, setAskAiHistory] = useState<{ 
    role: "user" | "assistant"; 
    text: string; 
    toolCalls?: any[]; 
    reasoningSummary?: string;
    sources?: string[];
    groundedConfidence?: string;
    richCards?: any[];
  }[]>([]);
  const [sessionId, setSessionId] = useState<string>("");
  useEffect(() => {
    setSessionId("sess_" + Math.random().toString(36).substring(7));
  }, []);
  const [isAskAiLoading, setIsAskAiLoading] = useState<boolean>(false);
  const [isReplayModalOpen, setIsReplayModalOpen] = useState<boolean>(false);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState<boolean>(false);
  const [bookingWorkflowStep, setBookingWorkflowStep] = useState<number>(-1);
  const [selectedReplayStageIndex, setSelectedReplayStageIndex] = useState<number>(-1);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [commandSearchQuery, setCommandSearchQuery] = useState<string>("");
  const [commandSearchResults, setCommandSearchResults] = useState<{
    patients: any[];
    providers: any[];
    services: any[];
    appointments: any[];
  }>({ patients: [], providers: [], services: [], appointments: [] });
  const [calendarViewMode, setCalendarViewMode] = useState<"day" | "week">("day");
  const [systemHealth, setSystemHealth] = useState<{
    status: string;
    details: {
      database: string;
      llm_provider: string;
      workers: string;
      notifications: string;
    };
  }>({
    status: "healthy",
    details: {
      database: "healthy",
      llm_provider: "healthy",
      workers: "healthy",
      notifications: "healthy"
    }
  });
  
  // Admin & Analytics Dashboard state
  const [currentView, setCurrentView] = useState<"operator" | "admin">("operator");
  const [adminConfig, setAdminConfig] = useState<any>({
    confidence_threshold: 0.85,
    alternative_slot_count: 3,
    fallback_model_enabled: true,
    logging_level: "INFO",
    weight_preferred_provider: 20.0,
    weight_back_to_back: 10.0,
    weight_small_gap: 5.0,
    weight_soonest_penalty: 0.5
  });
  const [adminAnalytics, setAdminAnalytics] = useState<any>(null);
  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState<boolean>(false);






  const searchInputRef = useRef<HTMLInputElement>(null);

  // Fetch baseline databases
  useEffect(() => {
    fetchMessages();
    fetchCRM();
    fetchAdminConfig();
    fetchAdminAnalytics();
    fetchSystemHealth();
  }, []);

  // Keyboard Navigation & Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isTyping = target && (
        target.tagName === "INPUT" || 
        target.tagName === "TEXTAREA" || 
        target.isContentEditable
      );

      // Listen for Ctrl+K
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
        setCommandSearchQuery("");
        setCommandSearchResults({ patients: [], providers: [], services: [], appointments: [] });
        return;
      }

      if (e.key === "Escape") {
        setIsCommandPaletteOpen(false);
        setIsReplayModalOpen(false);
        setIsSimulatorOpen(false);
        setSelectedReplayStageIndex(-1);
        if (isTyping) {
          target.blur();
        }
        return;
      }

      if (isTyping) {
        return;
      }

      if (e.key === "Tab") {
        e.preventDefault();
        navigateList(e.shiftKey ? -1 : 1);
        return;
      }

      if (e.key === " ") {
        if (selectedCase) {
          e.preventDefault();
          setIsReplayModalOpen(true);
          return;
        }
      }

      if (e.key === "/") {
        e.preventDefault();
        searchInputRef.current?.focus();
      } else if (e.key === "a" || e.key === "A") {
        if (decideResult?.outcome === "propose_booking") {
          handleApproveProposal();
        }
      } else if (e.key === "e" || e.key === "E") {
        handleEscalateManual();
      } else if (e.key === "c" || e.key === "C") {
        if (decideResult?.outcome === "ask_clarification") {
          handleSendClarification();
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        navigateList(1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        navigateList(-1);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedCase, decideResult, allMessages, activeQueue, searchQuery, isCommandPaletteOpen]);

  // Debounced search for command palette
  useEffect(() => {
    if (!commandSearchQuery.trim()) {
      setCommandSearchResults({ patients: [], providers: [], services: [], appointments: [] });
      return;
    }
    const delayDebounce = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(commandSearchQuery)}`);
        if (res.ok) {
          const data = await res.json();
          setCommandSearchResults(data);
        }
      } catch (err) {
        console.error(err);
      }
    }, 200);

    return () => clearTimeout(delayDebounce);
  }, [commandSearchQuery]);

  const fetchMessages = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/messages`);
      const data = await res.json();
      setAllMessages(data);
    } catch (err) {
      console.error("Failed to fetch messages:", err);
    }
  };

  const fetchCRM = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/crm`);
      const data = await res.json();
      setCrmData(data);
    } catch (err) {
      console.error("Failed to fetch CRM:", err);
    }
  };
  const fetchSystemHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
      }
    } catch (err) {
      console.error("Failed to fetch system health:", err);
    }
  };
  const fetchAdminConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config`);
      if (res.ok) {
        const data = await res.json();
        setAdminConfig(data);
      }
    } catch (err) {
      console.error("Failed to fetch admin config:", err);
    }
  };

  const fetchAdminAnalytics = async () => {
    setIsLoadingAnalytics(true);
    try {
      const res = await fetch(`${API_BASE}/api/analytics`);
      if (res.ok) {
        const data = await res.json();
        setAdminAnalytics(data);
      }
    } catch (err) {
      console.error("Failed to fetch admin analytics:", err);
    } finally {
      setIsLoadingAnalytics(false);
    }
  };

  const saveAdminConfig = async (updatedConfig: any) => {
    setIsSavingConfig(true);
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedConfig)
      });
      if (res.ok) {
        triggerToast("System configurations updated successfully!");
        fetchAdminConfig();
      } else {
        triggerToast("Failed to save configuration settings.");
      }
    } catch (err) {
      console.error(err);
      triggerToast("Error attempting to save configuration.");
    } finally {
      setIsSavingConfig(false);
    }
  };

  const runDecisionEngine = async (msg: Message) => {
    setIsDeciding(true);
    setDecideResult(null);
    setComposerText("");
    setOverrideReason("");
    setAskAiHistory([]);

    
    // Reset inline edit states to proposed values initially
    setEditedProviderId("");
    setEditedStartTime("");

    try {
      const res = await fetch(`${API_BASE}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(msg.input)
      });
      const data: DecideResponse = await res.json();
      setDecideResult(data);
      
      // Auto-load inline values
      if (data.booking_proposal) {
        setEditedProviderId(data.booking_proposal.provider_id);
        setEditedStartTime(data.booking_proposal.start_time);
      }
      
      // Resolve patient CRM details
      if (crmData && msg.input.patient_id) {
        const patient = crmData.patients.find(p => p.id === msg.input.patient_id);
        setSelectedPatientProfile(patient || null);
      } else {
        setSelectedPatientProfile(null);
      }
    } catch (err) {
      console.error("Failed to run decision:", err);
    } finally {
      setIsDeciding(false);
    }
  };

  const handleSelectCase = (msg: Message) => {
    setSelectedCase(msg);
    runDecisionEngine(msg);
  };

  const navigateList = (direction: number) => {
    const list = getFilteredMessages();
    if (list.length === 0) return;
    
    const currentIndex = selectedCase ? list.findIndex(m => m.id === selectedCase.id) : -1;
    let nextIndex = currentIndex + direction;
    if (nextIndex < 0) nextIndex = 0;
    if (nextIndex >= list.length) nextIndex = list.length - 1;
    
    handleSelectCase(list[nextIndex]);
  };

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // One-click approval route
  const handleApproveProposal = async () => {
    if (!selectedCase || !decideResult) return;

    const baseProposal = decideResult.booking_proposal;
    if (!baseProposal) return;

    // Build finalized proposal with inline overrides
    const finalProvider = crmData?.providers.find(p => p.id === editedProviderId);
    
    const finalProposal: Proposal = {
      ...baseProposal,
      provider_id: editedProviderId || baseProposal.provider_id,
      provider_name: finalProvider ? finalProvider.name : baseProposal.provider_name,
      start_time: editedStartTime || baseProposal.start_time,
    };

    try {
      setBookingWorkflowStep(0);
      const res = await fetch(`${API_BASE}/api/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: selectedCase.input.patient_id || "new_patient",
          provider_id: finalProposal.provider_id,
          service_id: finalProposal.service_id,
          start_time: finalProposal.start_time,
          duration_minutes: finalProposal.duration_minutes,
          price_usd: finalProposal.price_usd,
          rescheduled_appointment_id: finalProposal.rescheduled_appointment_id,
          override_reason: overrideReason || null,
          ai_proposal: baseProposal || null
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.status === "error" && data.error_type === "concurrency_conflict") {
          setBookingWorkflowStep(-1);
          triggerToast("⚠️ Conflict! " + data.message + " Check alternatives below.");
          setDecideResult(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              booking_proposal: {
                ...prev.booking_proposal!,
                alternatives: data.alternatives
              }
            };
          });
          return;
        }

        // Run step-by-step UI sequence
        setBookingWorkflowStep(1); // Saved to DB
        setTimeout(() => {
          setBookingWorkflowStep(2); // PDF Generated
          setTimeout(() => {
            setBookingWorkflowStep(3); // Email Sent
            setTimeout(() => {
              setBookingWorkflowStep(4); // SMS Sent
              setTimeout(() => {
                setBookingWorkflowStep(5); // Invite Created
                setTimeout(() => {
                  setBookingWorkflowStep(-1); // Complete & Close
                  
                  setCompletedList(prev => ({
                    ...prev,
                    [selectedCase.id]: {
                      proposal: finalProposal,
                      override_reason: overrideReason
                    }
                  }));
                  
                  if (data.pdf_filename) {
                    triggerToast("✅ Appointment confirmed! PDF receipt generated.");
                    window.open(`${API_BASE}/api/docs/download/${data.pdf_filename}`, "_blank");
                  } else {
                    triggerToast("Appointment confirmed & committed to CRM database!");
                  }
                  fetchCRM();
                }, 1000);
              }, 600);
            }, 600);
          }, 600);
        }, 600);
      } else {
        setBookingWorkflowStep(-1);
        triggerToast("Error: API confirmation failed.");
      }
    } catch (err) {
      console.error(err);
      setBookingWorkflowStep(-1);
      triggerToast("Error saving booking");
    }
  };

  // Keyboard or click Escalate
  const handleEscalateManual = () => {
    if (!selectedCase) return;
    setArchivedList(prev => ({ ...prev, [selectedCase.id]: true }));
    triggerToast("Conversation escalated & flagged for clinical manager.");
  };

  // Keyboard or click Clarify
  const handleSendClarification = () => {
    if (!selectedCase || !decideResult) return;
    setCompletedList(prev => ({
      ...prev,
      [selectedCase.id]: {
        proposal: {
          provider_id: "",
          provider_name: "",
          service_id: "",
          service_name: "",
          start_time: "",
          duration_minutes: 0,
          price_usd: 0
        },
        override_reason: "Clarification sent: " + (decideResult.question || "")
      }
    }));
    triggerToast("Clarification question dispatched to patient!");
  };

  // Alternative proposal override helper
  const selectAlternative = (alt: Proposal) => {
    setEditedProviderId(alt.provider_id);
    setEditedStartTime(alt.start_time);
    setOverrideReason("Human receptionist selected candidate slot override.");
    triggerToast(`Selected alternative slot: ${alt.provider_name} - ${alt.start_time}`);
  };

  const getSuggestedQuestions = () => {
    if (currentView === "admin") {
      return [
        "Show today's cancellations.",
        "What is the average provider utilization today?",
        "Provide a weekly revenue summary.",
        "Which provider had the most no-shows?",
        "Show daily metrics overview."
      ];
    } else {
      return [
        "Explain this decision.",
        "Why is confidence score low?",
        "What business rules were violated?",
        "Show Jordan's schedule.",
        "Show next Botox availability.",
        "Are there any VIP patients today?"
      ];
    }
  };

  const handleAskAi = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!askAiQuestion.trim() || !decideResult) return;

    const userQ = askAiQuestion.trim();
    setAskAiQuestion("");
    setAskAiHistory(prev => [...prev, { role: "user", text: userQ }]);
    setIsAskAiLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: decideResult,
          question: userQ,
          session_id: sessionId || null,
          ui_context: {
            selected_patient_id: selectedCase?.input.patient_id || null,
            selected_provider_id: editedProviderId || decideResult?.booking_proposal?.provider_id || null,
            selected_appointment_id: decideResult?.booking_proposal?.rescheduled_appointment_id || null,
            current_message_body: selectedCase?.input.message.body || null,
            current_decision_outcome: decideResult?.outcome || null,
            current_decision_confidence: decideResult?.confidence_score || null,
            current_decision_violated_rules: decideResult?.violated_rules || null,
            operator_role: "developer",
            current_view: currentView,
            clinic_id: "clinic_default"
          }
        })
      });

      if (res.ok) {
        const data = await res.json();
        setAskAiHistory(prev => [...prev, { 
          role: "assistant", 
          text: data.reply,
          toolCalls: data.tool_calls,
          reasoningSummary: data.reasoning_summary,
          sources: data.sources,
          groundedConfidence: data.grounded_confidence,
          richCards: data.rich_cards
        }]);
      } else {
        setAskAiHistory(prev => [...prev, { role: "assistant", text: "Error: Failed to fetch response from assistant." }]);
      }
    } catch (err) {
      console.error(err);
      setAskAiHistory(prev => [...prev, { role: "assistant", text: "Network error trying to contact explanation engine." }]);
    } finally {
      setIsAskAiLoading(false);
    }
  };


  // Run dynamic evaluation suite
  const runEvalsSuite = async () => {
    setIsRunningEvals(true);
    setEvalsResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/evals`);
      const data = await res.json();
      setEvalsResult(data);
      triggerToast("Evaluation suite executed successfully!");
    } catch (err) {
      console.error(err);
      triggerToast("Failed to run evaluation harness");
    } finally {
      setIsRunningEvals(false);
    }
  };

  // Filter messages dynamically based on status
  const getFilteredMessages = () => {
    return allMessages.filter(msg => {
      // 1. Text Search Filter
      const bodyText = msg.input.message.body.toLowerCase();
      const nameText = msg.note.toLowerCase();
      if (searchQuery && !bodyText.includes(searchQuery.toLowerCase()) && !nameText.includes(searchQuery.toLowerCase())) {
        return false;
      }
      
      // 2. Queue Status Filter
      const isCompleted = !!completedList[msg.id];
      const isArchived = !!archivedList[msg.id];
      
      if (activeQueue === "completed") return isCompleted;
      if (activeQueue === "archived") return isArchived;
      if (isCompleted || isArchived) return false; // Hide completed/archived from main review filters
      
      const queueType = msg.queue_type || "Evaluation";
      if (activeQueue === "live") return queueType === "Live";
      if (activeQueue === "simulation") return queueType === "Simulation";
      if (activeQueue === "evaluation") return queueType === "Evaluation";
      
      return true; // "all"
    });
  };

  // Check if anything was changed compared to the initial AI proposal
  const getDecisionDiff = () => {
    if (!decideResult || !decideResult.booking_proposal) return null;
    const ai = decideResult.booking_proposal;
    const changes: string[] = [];
    
    if (editedProviderId && editedProviderId !== ai.provider_id) {
      const prov = crmData?.providers.find(p => p.id === editedProviderId);
      changes.push(`Provider: ${ai.provider_name} → ${prov?.name || editedProviderId}`);
    }
    if (editedStartTime && editedStartTime !== ai.start_time) {
      changes.push(`Time: ${ai.start_time} → ${editedStartTime}`);
    }
    
    return changes.length > 0 ? changes : null;
  };

  const filteredMessages = getFilteredMessages();

  return (
    <div className="flex flex-col h-screen bg-brand-obsidian text-zinc-200">
      
      {/* HEADER BAR */}
      <header className="flex items-center justify-between border-b border-brand-border bg-brand-slate px-6 py-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-brand-champagne animate-pulse-ring"></div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-50">MyGlowTheory</h1>
          </div>
          
          <div className="flex items-center bg-brand-obsidian p-1 rounded-md border border-brand-border text-xs">
            <button
              onClick={() => setCurrentView("operator")}
              className={`px-3 py-1.5 rounded transition ${
                currentView === "operator" 
                  ? "bg-brand-border text-brand-champagne font-bold" 
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Operator Console
            </button>
            <button
              onClick={() => {
                setCurrentView("admin");
                fetchAdminAnalytics();
              }}
              className={`px-3 py-1.5 rounded transition ${
                currentView === "admin" 
                  ? "bg-brand-border text-brand-champagne font-bold" 
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Admin & Analytics
            </button>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setIsSimulatorOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-emerald text-brand-obsidian rounded font-bold text-xs hover:bg-emerald-600 transition shadow-lg shadow-brand-emerald/20"
          >
            <PlayCircle className="h-4 w-4" />
            Simulator
          </button>

          {/* Evals Status Widget */}
          <div className="flex items-center gap-3 border border-brand-border rounded px-3 py-1.5 bg-brand-obsidian text-xs">
            <span className="text-zinc-400">Eval Harness:</span>
            {evalsResult ? (
              <span className="font-semibold text-brand-emerald">
                {evalsResult.passed}/{evalsResult.total} ({evalsResult.score_pct}%)
              </span>
            ) : (
              <span className="font-semibold text-brand-champagne">Loaded</span>
            )}
            <button 
              onClick={runEvalsSuite}
              disabled={isRunningEvals}
              className="flex items-center gap-1 text-zinc-300 hover:text-brand-champagne disabled:opacity-50"
            >
              <RefreshCw className={`h-3 w-3 ${isRunningEvals ? "animate-spin" : ""}`} />
              Run Evals
            </button>
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <Activity className="h-4 w-4 text-brand-emerald" />
            <span>Groq Cloud Integration Connected</span>
          </div>
        </div>
      </header>

      {/* THREE-COLUMN WORKSPACE */}
      {currentView === "operator" ? (
        <div className="flex flex-1 overflow-hidden">
        
        {/* COLUMN 1: LEFT WORK QUEUE FEED */}
        <aside className="w-80 border-r border-brand-border flex flex-col bg-brand-obsidian">
          <div className="p-4 border-b border-brand-border">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search inbox... (Press '/')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-brand-slate border border-brand-border rounded-md pl-9 pr-4 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-brand-champagne"
              />
            </div>
          </div>
                 {/* Queues Filtering */}
          <div className="grid grid-cols-3 gap-1 p-2 bg-brand-slate border-b border-brand-border text-xs">
            <button 
              onClick={() => setActiveQueue("live")}
              className={`py-1.5 rounded transition ${activeQueue === "live" ? "bg-brand-obsidian text-brand-champagne font-semibold border border-brand-border" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              Live
            </button>
            <button 
              onClick={() => setActiveQueue("simulation")}
              className={`py-1.5 rounded transition ${activeQueue === "simulation" ? "bg-brand-obsidian text-brand-champagne font-semibold border border-brand-border" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              Simulation
            </button>
            <button 
              onClick={() => setActiveQueue("evaluation")}
              className={`py-1.5 rounded transition ${activeQueue === "evaluation" ? "bg-brand-obsidian text-brand-champagne font-semibold border border-brand-border" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              Evaluation
            </button>
          </div>
          <div className="grid grid-cols-2 gap-1 p-2 bg-brand-slate/50 border-b border-brand-border text-[10px]">
            <button 
              onClick={() => setActiveQueue("completed")}
              className={`py-1 rounded transition ${activeQueue === "completed" ? "bg-brand-obsidian text-brand-emerald font-semibold" : "text-zinc-500"}`}
            >
              ✓ Completed ({Object.keys(completedList).length})
            </button>
            <button 
              onClick={() => setActiveQueue("archived")}
              className={`py-1 rounded transition ${activeQueue === "archived" ? "bg-brand-obsidian text-zinc-300 font-semibold" : "text-zinc-500"}`}
            >
              Archived ({Object.keys(archivedList).length})
            </button>
          </div>

          {/* List queue */}
          <div className="flex-1 overflow-y-auto scrollable p-2 space-y-2">
            {filteredMessages.length === 0 ? (
              <div className="text-center py-10 text-xs text-zinc-500">
                No items in this queue filter.
              </div>
            ) : (
              filteredMessages.map((msg) => {
                const isSelected = selectedCase?.id === msg.id;
                const statusBadge = 
                  msg.expected_outcome === "propose_booking" ? "● Needs Review" :
                  msg.expected_outcome === "ask_clarification" ? "▲ Clarification" :
                  msg.expected_outcome === "escalate_to_human" ? "⚠ Escalated" :
                  "✓ Spam/Auto";
                  
                const colorClass = 
                  msg.expected_outcome === "propose_booking" ? "text-brand-emerald" :
                  msg.expected_outcome === "ask_clarification" ? "text-brand-champagne" :
                  msg.expected_outcome === "escalate_to_human" ? "text-brand-rose" :
                  "text-zinc-500";

                return (
                  <div
                    key={msg.id}
                    onClick={() => handleSelectCase(msg)}
                    className={`p-3 rounded-lg border text-left cursor-pointer transition ${
                      isSelected 
                        ? "bg-brand-slate border-brand-champagne" 
                        : "bg-brand-slate/40 border-brand-border hover:border-zinc-700"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-xs font-bold text-zinc-300 truncate">{msg.note}</span>
                      <span className={`text-[10px] font-semibold ${colorClass}`}>
                        {statusBadge}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400 line-clamp-2 mb-2">
                      {msg.input.message.body}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-zinc-500">
                      <span>{msg.input.message.channel.toUpperCase()}</span>
                      <span>Ref Clock: 05-18 14:30</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* COLUMN 2: CENTER ACTIVE WORKSPACE */}
        <section className="flex-1 flex flex-col bg-brand-obsidian">
          {!selectedCase ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 p-8">
              <Mail className="h-12 w-12 text-brand-border mb-4" />
              <h3 className="text-lg font-semibold text-zinc-400">Select triage item</h3>
              <p className="text-sm max-w-sm text-center mt-1">
                Pick a patient message from the queue sidebar to run the Live Groq Decision Pipeline.
              </p>
            </div>
          ) : (
            <div className="flex-1 flex flex-col overflow-hidden">
              
              {/* Patient header */}
              <div className="p-4 border-b border-brand-border bg-brand-slate flex justify-between items-center">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-md font-bold text-zinc-100">{selectedCase.note}</h2>
                    {selectedPatientProfile?.vip && (
                      <span className="rounded bg-purple-950/50 border border-purple-800 px-1.5 py-0.5 text-[10px] text-purple-300 font-semibold">
                        ★ VIP
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-zinc-500">
                    ID: {selectedCase.input.patient_id || "Unregistered lead"} • Channel: {selectedCase.input.message.channel.toUpperCase()}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={handleEscalateManual}
                    className="border border-brand-border hover:bg-brand-rose/10 hover:border-brand-rose text-brand-rose px-3 py-1.5 rounded text-xs transition"
                  >
                    Escalate
                  </button>
                  <button 
                    onClick={() => {
                      setArchivedList(prev => ({ ...prev, [selectedCase.id]: true }));
                      triggerToast("Case archived.");
                    }}
                    className="border border-brand-border hover:bg-zinc-800 text-zinc-300 px-3 py-1.5 rounded text-xs transition"
                  >
                    Archive
                  </button>
                </div>
              </div>

              {/* Chat Timeline bubbles */}
              <div className="flex-1 overflow-y-auto scrollable p-6 space-y-4">
                <div className="flex justify-start">
                  <div className="bg-brand-slate border border-brand-border rounded-lg p-4 max-w-md">
                    <p className="text-sm text-zinc-200">{selectedCase.input.message.body}</p>
                    <span className="text-[9px] text-zinc-500 block mt-2">
                      Patient Inbound • {selectedCase.input.message.from}
                    </span>
                  </div>
                </div>

                {isDeciding && (
                  <div className="flex justify-end animate-pulse">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 max-w-md flex items-center gap-3">
                      <div className="spinner h-4 w-4 border-2 border-brand-champagne border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-xs text-zinc-400">AI pipeline evaluating slot checks...</span>
                    </div>
                  </div>
                )}

                {decideResult && (
                  <div className="space-y-4">
                    {/* Live Decision Stages Lifecycle Tracker */}
                    <div className="p-4 border border-brand-border bg-brand-slate/40 rounded-lg text-xs">
                      <div className="flex items-center justify-between mb-2.5 text-[10px] text-zinc-400">
                        <div className="flex items-center gap-2">
                          <span>Decision Lifecycle Process</span>
                          <button
                            onClick={() => setIsReplayModalOpen(true)}
                            className="bg-brand-border hover:bg-zinc-800 text-brand-champagne border border-brand-border px-2 py-0.5 rounded text-[9px] font-bold tracking-tight transition"
                          >
                            Replay Decision
                          </button>
                        </div>

                        
                        {/* Confidence Block Bars */}
                        <div className="flex items-center gap-1.5">
                          <span className="text-zinc-500">Confidence:</span>
                          <div className="flex gap-0.5">
                            {[1, 2, 3].map((step) => {
                              const score = decideResult.confidence_score || 0;
                              let color = "bg-zinc-800";
                              if (score >= 0.95) color = "bg-emerald-500";
                              else if (score >= 0.85 && step <= 2) color = "bg-amber-500";
                              else if (score < 0.85 && step <= 1) color = "bg-red-500";
                              return <div key={step} className={`w-3.5 h-1.5 rounded-sm ${color}`} />;
                            })}
                          </div>
                          <span className="font-bold uppercase tracking-wider text-[9px] text-zinc-300">
                            {(decideResult.confidence_score || 0) >= 0.95 ? "High" : (decideResult.confidence_score || 0) >= 0.85 ? "Medium" : "Low"}
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {decideResult.event_stream && decideResult.event_stream.length > 0 ? (
                          decideResult.event_stream.map((ev, idx) => (
                            <React.Fragment key={`${ev.stage_name}-${idx}`}>
                              <div 
                                onClick={() => {
                                  setSelectedReplayStageIndex(idx);
                                  setIsReplayModalOpen(true);
                                }}
                                className="flex flex-col items-start px-2 py-1 rounded bg-brand-slate/60 border border-brand-border cursor-pointer hover:border-brand-champagne/80 hover:bg-brand-slate transition"
                              >
                                <span className="font-semibold text-zinc-300 text-[9px] uppercase tracking-wider">
                                  {ev.stage_name}
                                </span>
                                <span className="text-[8px] text-zinc-500 font-mono">
                                  {ev.duration_ms}ms
                                </span>
                              </div>
                              {idx < (decideResult.event_stream || []).length - 1 && <ChevronRight className="h-3 w-3 text-zinc-600" />}
                            </React.Fragment>
                          ))
                        ) : (
                          ["Receiving", "Understanding", "Checking Patient", "Checking Calendar", "Ranking Slots", "Ready"].map((s, idx) => {
                            const active = decideResult.decision_stages?.includes(s);
                            return (
                              <React.Fragment key={s}>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  active ? "bg-brand-champagne/10 text-brand-champagne border border-brand-champagne/20" : "bg-brand-border text-zinc-600 border border-transparent"
                                }`}>
                                  {s}
                                </span>
                                {idx < 5 && <ChevronRight className="h-3 w-3 text-zinc-600" />}
                              </React.Fragment>
                            );
                          })
                        )}
                      </div>
                    </div>

                    {/* Explainability Checklist */}
                    <div className="bg-brand-slate/40 border border-brand-border rounded-lg p-3 my-3">
                      <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-2">Decision Verification</div>
                      <div className="grid grid-cols-5 gap-2">
                        {[
                          { label: "Intent", check: !!decideResult.outcome },
                          { label: "Patient", check: !!decideResult.booking_proposal?.provider_id || decideResult.outcome === "escalate_to_human" || decideResult.outcome === "ask_clarification" },
                          { label: "Calendar", check: !!decideResult.booking_proposal?.start_time || decideResult.outcome !== "propose_booking" },
                          { label: "Specialty", check: !!decideResult.booking_proposal?.service_id || decideResult.outcome !== "propose_booking" },
                          { label: "Ranking", check: (decideResult.booking_proposal?.alternatives && decideResult.booking_proposal.alternatives.length > 0) || decideResult.outcome !== "propose_booking" },
                        ].map((item) => (
                          <div key={item.label} className={`flex items-center gap-1.5 px-2 py-1.5 rounded text-[10px] font-semibold border ${
                            item.check 
                              ? "bg-emerald-950/30 text-emerald-400 border-emerald-800/50" 
                              : "bg-zinc-900/30 text-zinc-600 border-zinc-800/50"
                          }`}>
                            <span>{item.check ? "✔" : "○"}</span>
                            <span>{item.label}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* AI Decision Panel output representation */}
                    <div className="flex justify-end">
                      <div className="bg-brand-slate border border-brand-border rounded-lg p-5 max-w-xl w-full">
                        <div className="flex items-center justify-between pb-3 border-b border-brand-border mb-3">
                          <div className="flex items-center gap-2">
                            <Sparkles className="h-4 w-4 text-brand-champagne" />
                            <span className="text-sm font-bold text-zinc-100">Live AI Output</span>
                          </div>
                          <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${
                            decideResult.outcome === "propose_booking" ? "bg-emerald-950 text-brand-emerald border border-emerald-800" :
                            decideResult.outcome === "ask_clarification" ? "bg-amber-950 text-brand-champagne border border-amber-800" :
                            decideResult.outcome === "escalate_to_human" ? "bg-red-950 text-brand-rose border border-red-800" :
                            "bg-zinc-800 text-zinc-400"
                          }`}>
                            {decideResult.outcome.replace("_", " ")}
                          </span>
                        </div>

                        {/* OUTCOME CONTENT: ESCALATE */}
                        {decideResult.outcome === "escalate_to_human" && (
                          <div className="bg-red-950/20 border border-red-900/50 p-3.5 rounded text-sm text-brand-rose flex gap-3">
                            <AlertOctagon className="h-5 w-5 flex-shrink-0" />
                            <div>
                              <strong className="block mb-0.5">Escalated to Staff</strong>
                              <p className="text-zinc-300">{decideResult.reason}</p>
                            </div>
                          </div>
                        )}

                        {/* OUTCOME CONTENT: CLARIFICATION */}
                        {decideResult.outcome === "ask_clarification" && (
                          <div className="bg-amber-950/20 border border-amber-900/50 p-3.5 rounded text-sm text-brand-champagne flex gap-3">
                            <HelpCircle className="h-5 w-5 flex-shrink-0" />
                            <div>
                              <strong className="block mb-0.5">Pending Patient Clarification</strong>
                              <p className="text-zinc-300">{decideResult.question}</p>
                            </div>
                          </div>
                        )}

                        {/* OUTCOME CONTENT: PROPOSE BOOKING */}
                        {decideResult.outcome === "propose_booking" && decideResult.booking_proposal && (
                          <div className="space-y-3">
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div className="bg-brand-obsidian border border-brand-border p-2.5 rounded">
                                <label className="text-zinc-500 block mb-0.5 text-[10px]">SERVICE</label>
                                <span className="font-semibold text-zinc-200">
                                  {decideResult.booking_proposal.service_name}
                                </span>
                              </div>
                              <div className="bg-brand-obsidian border border-brand-border p-2.5 rounded">
                                <label className="text-zinc-500 block mb-0.5 text-[10px]">PROVIDER</label>
                                <span className="font-semibold text-zinc-200">
                                  {decideResult.booking_proposal.provider_name}
                                </span>
                              </div>
                              <div className="bg-brand-obsidian border border-brand-border p-2.5 rounded col-span-2 flex items-center justify-between">
                                <div>
                                  <label className="text-zinc-500 block mb-0.5 text-[10px]">PROPOSED APPOINTMENT SLOT</label>
                                  <span className="font-semibold text-brand-emerald">
                                    {new Date(decideResult.booking_proposal.start_time).toLocaleString("en-US", {
                                      weekday: "long", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
                                    })}
                                  </span>
                                </div>
                                <div className="text-right">
                                  <span className="text-amber-500 block text-xs">★★★★★</span>
                                  <span className="text-[8px] uppercase tracking-wider text-brand-champagne font-bold">Recommended</span>
                                </div>
                              </div>
                            </div>
                            
                            {decideResult.rationale && (
                              <div className="text-xs bg-brand-obsidian border border-brand-border p-3 rounded text-zinc-300 leading-relaxed">
                                <strong className="text-[10px] text-zinc-500 block mb-1">REASONING EXPLANATION</strong>
                                {decideResult.rationale}
                              </div>
                            )}

                            {/* Decision Diff Section */}
                            {getDecisionDiff() && (
                              <div className="bg-purple-950/20 border border-purple-900/50 p-2.5 rounded text-xs text-purple-300">
                                <span className="font-bold block mb-1">Human Overrides Applied:</span>
                                <ul className="list-disc list-inside space-y-0.5">
                                  {getDecisionDiff()?.map((diff, i) => <li key={i}>{diff}</li>)}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}

                        {/* VIOLATED RULES WARNINGS */}
                        {decideResult.violated_rules && decideResult.violated_rules.length > 0 && (
                          <div className="mt-3 p-3 bg-red-950/10 border border-brand-border rounded flex flex-col gap-1.5 text-xs text-brand-rose">
                            <span className="font-bold flex items-center gap-1.5">
                              <ShieldAlert className="h-4 w-4" /> Violated Safety/Business Rules:
                            </span>
                            <div className="flex gap-2 flex-wrap mt-1">
                              {decideResult.violated_rules.map(rule => (
                                <span key={rule} className="bg-brand-rose/10 px-2 py-0.5 rounded text-[10px] border border-brand-rose/20 uppercase font-semibold">
                                  {rule.replace("_", " ")}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* CONFIRMATION life controls */}
                        <div className="mt-4 pt-3 border-t border-brand-border flex items-center justify-between gap-3">
                          <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                            <Clock className="h-3 w-3" /> Latency: {decideResult.metadata?.latency_ms}ms
                          </span>
                          <div className="flex gap-2">
                            {decideResult.outcome === "propose_booking" && (
                              <button
                                onClick={handleApproveProposal}
                                className="bg-brand-emerald hover:bg-brand-emerald/90 text-zinc-950 font-semibold px-4 py-2 rounded text-xs flex items-center gap-1.5 transition"
                              >
                                <CheckCircle className="h-4 w-4" /> Confirm & Schedule (A)
                              </button>
                            )}
                            {decideResult.outcome === "ask_clarification" && (
                              <button
                                onClick={handleSendClarification}
                                className="bg-brand-champagne hover:bg-brand-champagne/90 text-zinc-950 font-semibold px-4 py-2 rounded text-xs flex items-center gap-1.5 transition"
                              >
                                <Send className="h-4 w-4" /> Send Clarification (C)
                              </button>
                            )}
                            {decideResult.outcome === "escalate_to_human" && (
                              <button
                                onClick={handleEscalateManual}
                                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-semibold px-4 py-2 rounded text-xs flex items-center gap-1.5 transition"
                              >
                                Take Over Manual (E)
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Show finalized confirmed receipt representation */}
                {completedList[selectedCase.id] && (
                  <div className="flex justify-end">
                    <div className="bg-brand-slate border border-brand-border text-xs rounded-lg p-4 max-w-sm flex items-start gap-3 border-l-4 border-l-brand-emerald shadow-lg">
                      <Check className="h-5 w-5 text-brand-emerald flex-shrink-0 mt-0.5" />
                      <div>
                        <strong className="block text-zinc-200 font-semibold mb-1">Appointment Successfully Logged</strong>
                        <p className="text-zinc-400">
                          Scheduled for {completedList[selectedCase.id].proposal.start_time ? new Date(completedList[selectedCase.id].proposal.start_time).toLocaleString() : "Manual text response dispatch"}.
                        </p>
                        {completedList[selectedCase.id].override_reason && (
                          <span className="text-[10px] text-brand-champagne block mt-1.5 italic">
                            Details: {completedList[selectedCase.id].override_reason}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Composition Workspace */}
              <div className="p-4 border-t border-brand-border bg-brand-slate">
                <div className="flex gap-3">
                  <textarea
                    placeholder="Type an inline response to patient..."
                    value={composerText}
                    onChange={(e) => setComposerText(e.target.value)}
                    className="flex-1 bg-brand-obsidian border border-brand-border rounded-md px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-brand-champagne min-h-[48px] max-h-[120px]"
                  />
                  <button 
                    onClick={() => {
                      if (!composerText) return;
                      setCompletedList(prev => ({
                        ...prev,
                        [selectedCase.id]: {
                          proposal: {
                            provider_id: "",
                            provider_name: "",
                            service_id: "",
                            service_name: "",
                            start_time: "",
                            duration_minutes: 0,
                            price_usd: 0
                          },
                          override_reason: "Manual Response Sent: " + composerText
                        }
                      }));
                      triggerToast("Manual message text dispatched!");
                      setComposerText("");
                    }}
                    className="bg-brand-border hover:bg-zinc-800 text-zinc-300 px-4 rounded-md transition flex items-center justify-center"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
                <div className="flex items-center justify-between mt-2.5 text-[10px] text-zinc-500">
                  <span className="flex items-center gap-1">
                    Keyboard: <kbd className="bg-brand-border px-1.5 py-0.5 rounded text-[9px]">A</kbd> Approve • 
                    <kbd className="bg-brand-border px-1.5 py-0.5 rounded text-[9px] ml-1">E</kbd> Escalate • 
                    <kbd className="bg-brand-border px-1.5 py-0.5 rounded text-[9px] ml-1">C</kbd> Clarify
                  </span>
                  <span>Press Up/Down arrow to scroll messages</span>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* COLUMN 3: RIGHT EXPLAINABILITY & CRM PANEL */}
        <aside className="w-80 border-l border-brand-border flex flex-col bg-brand-slate/40">
          {/* Tab selectors */}
          <div className="flex border-b border-brand-border bg-brand-slate text-[10px]">
            <button 
              onClick={() => setActiveTabRight("decision")}
              className={`flex-1 py-3 text-center transition font-semibold ${activeTabRight === "decision" ? "text-brand-champagne border-b-2 border-brand-champagne" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              AI Explain
            </button>
            <button 
              onClick={() => setActiveTabRight("crm")}
              className={`flex-1 py-3 text-center transition font-semibold ${activeTabRight === "crm" ? "text-brand-champagne border-b-2 border-brand-champagne" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              CRM Summary
            </button>
            <button 
              onClick={() => setActiveTabRight("calendar")}
              className={`flex-1 py-3 text-center transition font-semibold ${activeTabRight === "calendar" ? "text-brand-champagne border-b-2 border-brand-champagne" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              Calendar Map
            </button>
            <button 
              onClick={() => setActiveTabRight("activity")}
              className={`flex-1 py-3 text-center transition font-semibold ${activeTabRight === "activity" ? "text-brand-champagne border-b-2 border-brand-champagne" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              Audit Feed
            </button>
          </div>

          <div className="flex-1 overflow-y-auto scrollable p-4 space-y-4">
            
            {/* VIEW TAB 1: DECISION EXPLAIN */}
            {activeTabRight === "decision" && (
              <div className="space-y-4 animate-fade-in">
                {!decideResult ? (
                  <div className="text-zinc-500 text-center py-10 text-xs">
                    No active decision to explain.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Appointment Workflow Progress Timeline */}
                    <div className="bg-brand-slate border border-brand-border p-4 rounded-lg">
                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                        <CheckCircle className="h-4 w-4 text-brand-champagne" /> Appointment Workspace Stage
                      </h4>
                      <div className="flex items-center justify-between text-[9px] font-semibold text-zinc-500 font-mono">
                        {[
                          { label: "Received", done: true },
                          { label: "AI Propose", done: true },
                          { label: "Operator Review", done: true },
                          { label: "Confirmed", done: selectedCase?.status === "booked" || decideResult?.outcome === "propose_booking" },
                          { label: "Completed", done: selectedCase?.status === "completed" }
                        ].map((step, idx) => (
                          <div key={idx} className="flex flex-col items-center gap-1">
                            <div className={`h-4 w-4 rounded-full flex items-center justify-center text-[9px] font-bold ${
                              step.done ? "bg-brand-emerald text-zinc-950" : "bg-brand-border text-zinc-500"
                            }`}>
                              {idx + 1}
                            </div>
                            <span className={step.done ? "text-brand-emerald font-bold" : "text-zinc-500"}>
                              {step.label}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* Pipeline Strategy */}
                    <div className="bg-brand-slate border border-brand-border p-4 rounded-lg">
                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                        <Award className="h-4 w-4 text-brand-champagne" /> Pipeline Strategy
                      </h4>
                      <div className="space-y-2 text-xs text-zinc-400 leading-relaxed">
                        <p>
                          <strong>Core Resolution:</strong> Identified client classification as 
                          <span className="text-brand-champagne font-semibold font-mono ml-1">
                            {decideResult.outcome}
                          </span>.
                        </p>
                        {decideResult.booking_proposal && (
                          <p>
                            <strong>Inference Strategy:</strong> Pre-validated against `do_not_book` registry check. 
                            Provider specialty validation succeeded for provider ID `{decideResult.booking_proposal.provider_id}`.
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Extraction & Resolution */}
                    <div className="bg-brand-slate border border-brand-border p-4 rounded-lg">
                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                        <Cpu className="h-4 w-4 text-brand-champagne" /> Extraction & Resolution
                      </h4>
                      <div className="space-y-2 text-xs text-zinc-400">
                        <div className="flex justify-between border-b border-brand-border/40 pb-1.5">
                          <span className="text-zinc-500">Service Query:</span>
                          <span className="text-zinc-300 font-semibold">{decideResult.metadata?.extracted_service || "Not Specified"}</span>
                        </div>
                        <div className="flex justify-between border-b border-brand-border/40 pb-1.5">
                          <span className="text-zinc-500">Provider Query:</span>
                          <span className="text-zinc-300 font-semibold">{decideResult.metadata?.extracted_provider || "Any Provider"}</span>
                        </div>
                        <div className="flex justify-between border-b border-brand-border/40 pb-1.5">
                          <span className="text-zinc-500">Time Text:</span>
                          <span className="text-zinc-300 font-mono">{decideResult.metadata?.extracted_time_text || "Not Specified"}</span>
                        </div>
                        {decideResult.metadata?.resolved_time_boundary && (
                          <div className="pt-1">
                            <span className="text-zinc-500 block mb-1">Resolved Search Window:</span>
                            <div className="bg-brand-obsidian p-2 rounded text-[10px] font-mono text-brand-champagne border border-brand-border/50">
                              <div>Start: {new Date(decideResult.metadata.resolved_time_boundary.start_search).toLocaleString()}</div>
                              <div>End: {new Date(decideResult.metadata.resolved_time_boundary.end_search).toLocaleString()}</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Rule Inspector */}
                    <div className="bg-brand-slate border border-brand-border p-4 rounded-lg">
                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                        <ShieldAlert className="h-4 w-4 text-brand-champagne" /> Rule Inspector
                      </h4>
                      <div className="space-y-2 text-xs">
                        {[
                          { key: "do_not_book", label: "Patient Registry (Do Not Book)" },
                          { key: "medical_safety", label: "Clinical Safety Firewall" },
                          { key: "specialty_mismatch", label: "Provider Specialty Alignment" },
                          { key: "after_hours", label: "Working Hours Verification" },
                          { key: "security_threat", label: "Security & Anti-Impersonation" },
                        ].map((rule) => {
                          const violated = decideResult.violated_rules?.includes(rule.key);
                          return (
                            <div key={rule.key} className="flex items-center justify-between py-1 border-b border-brand-border/40 last:border-b-0">
                              <span className="text-zinc-400">{rule.label}</span>
                              <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                                violated 
                                  ? "bg-red-950 text-brand-rose border border-red-900/50 animate-pulse" 
                                  : "bg-emerald-950 text-brand-emerald border border-emerald-900/50"
                              }`}>
                                {violated ? "✕ FAILED" : "✓ PASSED"}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Expose computed runner-up alternative proposals */}
                    {decideResult.outcome === "propose_booking" && (
                      <div className="bg-brand-slate border border-brand-border p-4 rounded-lg">
                        <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                          <Clock className="h-4 w-4 text-brand-emerald" /> Alternative Slots Computed
                        </h4>
                        
                        {!decideResult.alternative_proposals || decideResult.alternative_proposals.length === 0 ? (
                          <span className="text-[10px] text-zinc-500">No alternate candidate slots found.</span>
                        ) : (
                          <div className="space-y-2.5">
                            {decideResult.alternative_proposals.map((alt, idx) => {
                              const stars = idx === 0 ? "★★★★☆" : idx === 1 ? "★★★★☆" : "★★★☆☆";
                              const ratingLabel = idx === 0 ? "Second Option" : idx === 1 ? "Alternative" : "Last Choice";
                              return (
                                <div 
                                  key={idx}
                                  onClick={() => selectAlternative(alt)}
                                  className="bg-brand-obsidian border border-brand-border hover:border-brand-champagne p-2.5 rounded cursor-pointer transition text-[11px]"
                                >
                                  <div className="flex justify-between font-bold mb-0.5 text-zinc-300">
                                    <span>{alt.provider_name}</span>
                                    <span className="text-brand-emerald">${alt.price_usd}</span>
                                  </div>
                                  <div className="flex items-center justify-between mt-1 text-zinc-500 text-[10px]">
                                    <span>
                                      {new Date(alt.start_time).toLocaleString("en-US", {
                                        weekday: "short", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit"
                                      })}
                                    </span>
                                    <span className="text-amber-500 flex items-center gap-1">
                                      <span className="text-[9px]">{stars}</span>
                                      <span className="text-[8px] uppercase tracking-wider text-zinc-400 font-semibold">{ratingLabel}</span>
                                    </span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Notification & Confirmations Logs */}
                    <div className="bg-brand-slate border border-brand-border p-4 rounded-lg text-xs">
                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                        <Mail className="h-4 w-4 text-brand-champagne" /> Confirmation Logs
                      </h4>
                      <div className="space-y-1.5 text-zinc-400 font-mono text-[10px]">
                        <div className="flex justify-between">
                          <span>SMS Dispatch:</span>
                          <span className="text-brand-emerald font-semibold">✔ DISPATCHED (+1 310-555-0199)</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Email Dispatch:</span>
                          <span className="text-brand-emerald font-semibold">✔ DISPATCHED (sent confirmation link)</span>
                        </div>
                        <div className="flex justify-between">
                          <span>PDF Generator:</span>
                          <span className="text-brand-emerald font-semibold">✔ COMPILED (128KB check-in sheet)</span>
                        </div>
                      </div>
                    </div>

                    {/* Telemetry metadata drawer */}
                    <div className="bg-brand-slate/30 border border-brand-border p-3.5 rounded-lg text-[10px] space-y-1.5 font-mono text-zinc-500">
                      <div className="flex justify-between">
                        <span>API Provider:</span>
                        <span className="text-zinc-400">{decideResult.metadata?.api_provider}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Model:</span>
                        <span className="text-zinc-400 truncate max-w-[120px]">{decideResult.metadata?.model}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Latency:</span>
                        <span className="text-zinc-400">{decideResult.metadata?.latency_ms} ms</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Timestamp:</span>
                        <span className="text-zinc-400 truncate max-w-[120px]">{decideResult.metadata?.timestamp}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* VIEW TAB 2: CRM MINI CARD */}
            {activeTabRight === "crm" && (
              <div className="space-y-4 animate-fade-in">
                {!selectedPatientProfile ? (
                  <div className="text-zinc-500 text-center py-10 text-xs">
                    No matching CRM patient record resolved.
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="bg-brand-slate border border-brand-border p-4 rounded-lg flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-brand-border flex items-center justify-center text-sm font-bold text-brand-champagne border border-brand-border">
                        {selectedPatientProfile.name.split(" ").map((n: string) => n[0]).join("")}
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-zinc-100">{selectedPatientProfile.name}</h4>
                        <span className="text-[10px] text-zinc-500">{selectedPatientProfile.email}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-center text-xs">
                      <div className="bg-brand-slate border border-brand-border p-3 rounded">
                        <span className="text-zinc-500 text-[10px] block mb-1 uppercase">Preferred Provider</span>
                        <span className="font-bold text-zinc-300">
                          {selectedPatientProfile.preferred_provider_id === "prov_1" ? "Amelia Reyes" :
                           selectedPatientProfile.preferred_provider_id === "prov_2" ? "Jordan Patel" :
                           selectedPatientProfile.preferred_provider_id === "prov_3" ? "Maya Lin" : "Imani Vance"}
                        </span>
                      </div>
                      <div className="bg-brand-slate border border-brand-border p-3 rounded">
                        <span className="text-zinc-500 text-[10px] block mb-1 uppercase">Marketing Opt-Out</span>
                        <span className="font-bold text-zinc-300">
                          {selectedPatientProfile.marketing_opt_out ? "Yes" : "No"}
                        </span>
                      </div>
                    </div>

                    {selectedPatientProfile.notes && (
                      <div className="bg-brand-slate border border-brand-border p-3 rounded text-xs text-zinc-400 leading-relaxed">
                        <strong className="text-[10px] text-zinc-500 block mb-1 uppercase">Staff Notes</strong>
                        {selectedPatientProfile.notes}
                      </div>
                    )}

                    {selectedPatientProfile.tags && selectedPatientProfile.tags.length > 0 && (
                      <div className="bg-brand-slate border border-brand-border p-3 rounded text-xs">
                        <strong className="text-[10px] text-zinc-500 block mb-1.5 uppercase">Treatment Tags</strong>
                        <div className="flex gap-1.5 flex-wrap">
                          {selectedPatientProfile.tags.map((tag: string) => (
                            <span key={tag} className="bg-brand-border text-zinc-400 px-1.5 py-0.5 rounded text-[10px]">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Patient Medical Timeline */}
                    <div className="bg-brand-slate border border-brand-border p-3 rounded text-xs">
                      <strong className="text-[10px] text-zinc-500 block mb-2.5 uppercase font-bold tracking-wider">Medical History Timeline</strong>
                      <div className="relative border-l border-brand-border pl-4 space-y-4 ml-1">
                        {crmData.appointments && crmData.appointments.filter((a: any) => a.patient_id === selectedPatientProfile.id).length > 0 ? (
                          crmData.appointments
                            .filter((a: any) => a.patient_id === selectedPatientProfile.id)
                            .sort((a: any, b: any) => b.start.localeCompare(a.start))
                            .map((appt: any, index: number) => {
                              const apptDate = new Date(appt.start).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
                              const serviceName = crmData.services?.find((s: any) => s.id === appt.service_id)?.name || appt.service_id;
                              const providerName = crmData.providers?.find((p: any) => p.id === appt.provider_id)?.name || appt.provider_id;
                              
                              let statusBadge = "bg-brand-emerald/10 text-brand-emerald border-brand-emerald/30";
                              if (appt.status === "cancelled") statusBadge = "bg-brand-rose/10 text-brand-rose border-brand-rose/30";
                              if (appt.status === "no_show") statusBadge = "bg-amber-500/10 text-amber-500 border-amber-500/30";
                              if (appt.status === "booked") statusBadge = "bg-brand-champagne/10 text-brand-champagne border-brand-champagne/30";

                              return (
                                <div key={appt.id || index} className="relative">
                                  {/* Timeline dot */}
                                  <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-brand-border border border-brand-slate" />
                                  <div className="space-y-1">
                                    <div className="flex justify-between items-center text-[10px]">
                                      <span className="text-zinc-400 font-bold">{apptDate}</span>
                                      <span className={`px-1 py-0.5 rounded border text-[8px] font-semibold ${statusBadge}`}>
                                        {appt.status.replace("_", " ").toUpperCase()}
                                      </span>
                                    </div>
                                    <div className="text-zinc-200 text-xs font-semibold">
                                      {serviceName} with {providerName}
                                    </div>
                                  </div>
                                </div>
                              );
                            })
                        ) : (
                          <div className="text-zinc-500 italic text-[11px] pl-1">
                            No previous appointments found on file.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* VIEW TAB 3: CALENDAR MAP */}
            {activeTabRight === "calendar" && (
              <div className="space-y-4 animate-fade-in">
                {/* Proposed inline editor for appointment validation overrides */}
                {decideResult?.booking_proposal && (
                  <div className="bg-brand-slate border border-brand-border p-4 rounded-lg space-y-3.5">
                    <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Calendar className="h-4 w-4 text-brand-champagne" /> Manual Adjustment Override
                    </h4>
                    
                    {/* Inline fields mapping */}
                    <div className="space-y-2 text-xs">
                      <div>
                        <label className="text-zinc-500 block mb-1">Assigned Provider</label>
                        <select 
                          value={editedProviderId} 
                          onChange={(e) => {
                            setEditedProviderId(e.target.value);
                            setOverrideReason("Human receptionist overrode selected provider.");
                          }}
                          className="w-full bg-brand-obsidian border border-brand-border rounded px-2.5 py-2 text-zinc-300 focus:outline-none focus:border-brand-champagne"
                        >
                          {crmData?.providers.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>
                      </div>
                      
                      <div>
                        <label className="text-zinc-500 block mb-1">Start Time (UTC Offset format)</label>
                        <input 
                          type="text" 
                          value={editedStartTime} 
                          onChange={(e) => {
                            setEditedStartTime(e.target.value);
                            setOverrideReason("Human receptionist overrode proposed start time.");
                          }}
                          className="w-full bg-brand-obsidian border border-brand-border rounded px-2.5 py-2 text-zinc-300 focus:outline-none focus:border-brand-champagne font-mono"
                        />
                      </div>

                      <div>
                        <label className="text-zinc-500 block mb-1">Human Override Reason (diff telemetry log)</label>
                        <input 
                          type="text" 
                          placeholder="e.g. Patient requested Dr. Reyes specifically"
                          value={overrideReason} 
                          onChange={(e) => setOverrideReason(e.target.value)}
                          className="w-full bg-brand-obsidian border border-brand-border rounded px-2.5 py-2 text-zinc-300 focus:outline-none focus:border-brand-champagne"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Calendar View Selector and representation */}
                <div className="bg-brand-slate border border-brand-border p-4 rounded-lg space-y-3">
                  <div className="flex items-center justify-between text-xs pb-1 border-b border-brand-border">
                    <span className="font-bold text-zinc-300">Enterprise Scheduler</span>
                    <div className="flex gap-1">
                      <button 
                        onClick={() => setCalendarViewMode("day")}
                        className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${calendarViewMode === "day" ? "bg-brand-champagne text-zinc-950" : "bg-brand-border text-zinc-400 hover:text-zinc-200"}`}
                      >
                        Day View
                      </button>
                      <button 
                        onClick={() => setCalendarViewMode("week")}
                        className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${calendarViewMode === "week" ? "bg-brand-champagne text-zinc-950" : "bg-brand-border text-zinc-400 hover:text-zinc-200"}`}
                      >
                        Week View
                      </button>
                    </div>
                  </div>

                  {calendarViewMode === "day" ? (
                    <div className="space-y-1.5 max-h-[260px] overflow-y-auto scrollable pr-1 text-[11px] font-mono">
                      {["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"].map((hr) => {
                        const dayAppts = crmData?.appointments?.filter((a: any) => {
                          if (a.provider_id !== editedProviderId || a.status === "cancelled") return false;
                          const apptHour = new Date(a.start).getHours();
                          const hrNum = parseInt(hr.split(":")[0]) + (hr.includes("PM") && !hr.startsWith("12") ? 12 : 0);
                          return apptHour === hrNum;
                        }) || [];

                        const isProposedTime = decideResult?.booking_proposal && (() => {
                          const propHour = new Date(decideResult.booking_proposal.start_time).getHours();
                          const hrNum = parseInt(hr.split(":")[0]) + (hr.includes("PM") && !hr.startsWith("12") ? 12 : 0);
                          return propHour === hrNum && editedProviderId === decideResult.booking_proposal.provider_id;
                        })();

                        return (
                          <div key={hr} className="flex items-center justify-between border-b border-brand-border/40 py-2">
                            <span className="text-zinc-500">{hr}</span>
                            <div className="flex gap-1.5 flex-1 justify-end ml-4">
                              {dayAppts.length > 0 ? (
                                dayAppts.map((appt: any) => {
                                  const pName = crmData.patients?.find((p: any) => p.id === appt.patient_id)?.name || appt.patient_id;
                                  return (
                                    <div 
                                      key={appt.id} 
                                      draggable
                                      onDragStart={(e) => {
                                        e.dataTransfer.setData("text/plain", appt.id);
                                        triggerToast("Dragging appointment to reschedule...");
                                      }}
                                      className="bg-brand-border text-zinc-300 border border-brand-champagne/25 rounded px-2 py-0.5 text-[9px] cursor-grab active:cursor-grabbing hover:border-brand-champagne transition flex items-center justify-between gap-1 max-w-[120px] truncate"
                                    >
                                      <span>{pName}</span>
                                    </div>
                                  );
                                })
                              ) : isProposedTime ? (
                                <span className="bg-emerald-950 text-brand-emerald border border-brand-emerald/30 rounded px-2 py-0.5 text-[9px] font-bold animate-pulse">
                                  Proposed Slot
                                </span>
                              ) : (
                                <div 
                                  onDragOver={(e) => e.preventDefault()}
                                  onDrop={(e) => {
                                    e.preventDefault();
                                    const apptId = e.dataTransfer.getData("text/plain");
                                    triggerToast(`Rescheduled Appointment ${apptId} to ${hr}. Triggering rule validation...`);
                                  }}
                                  className="text-[9px] text-brand-emerald/30 border border-dashed border-brand-emerald/10 hover:border-brand-emerald/30 px-2 py-0.5 rounded transition cursor-pointer"
                                >
                                  Available
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="grid grid-cols-5 gap-1 text-[9px] text-center font-mono py-2">
                      {["Mon", "Tue", "Wed", "Thu", "Fri"].map((day, idx) => {
                        const dayNum = 18 + idx;
                        const dayAppts = crmData?.appointments?.filter((a: any) => {
                          if (a.provider_id !== editedProviderId || a.status === "cancelled") return false;
                          const apptDay = new Date(a.start).getDate();
                          return apptDay === dayNum;
                        }) || [];

                        return (
                          <div key={day} className="bg-brand-obsidian/45 border border-brand-border p-2 rounded flex flex-col items-center space-y-1">
                            <span className="text-zinc-500 font-bold">{day}</span>
                            <span className="text-zinc-400 font-bold">{18 + idx}</span>
                            <div className="w-full mt-2 space-y-1">
                              {dayAppts.map((appt: any) => (
                                <div 
                                  key={appt.id} 
                                  className="bg-brand-border text-zinc-300 rounded py-0.5 text-[8px] border border-transparent hover:border-brand-champagne/40 truncate px-1"
                                  title={appt.id}
                                >
                                  {appt.status === "booked" ? "●" : "○"}
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* VIEW TAB 4: AUDIT FEED */}
            {activeTabRight === "activity" && (
              <div className="space-y-3.5 animate-fade-in text-xs">
                <div className="flex justify-between items-center pb-2 border-b border-brand-border">
                  <h4 className="font-bold text-zinc-300 uppercase tracking-wider">Clinic Activity Feed</h4>
                  <span className="text-[10px] bg-brand-border text-zinc-400 px-2 py-0.5 rounded">Real-time</span>
                </div>
                
                <div className="space-y-3.5 max-h-[70vh] overflow-y-auto scrollable pr-1.5">
                  {[
                    { time: "Just Now", type: "system", title: "PDF Confirmation Compiled", desc: "Generated check-in instructions PDF for Sarah", status: "success" },
                    { time: "2 mins ago", type: "sms", title: "SMS Dispatch Prepared", desc: "Pre-appointment reminder sent to +1 (310) 555-0199", status: "success" },
                    { time: "5 mins ago", type: "email", title: "Email Invites Generated", desc: "Sent calendar confirmation link to sarah.j@example.com", status: "success" },
                    { time: "10 mins ago", type: "override", title: "Operator Override Recorded", desc: "Jordan changed appointment start time for patient Sarah", status: "warning" },
                    { time: "15 mins ago", type: "ai", title: "AI Proposal Generated", desc: "Decision context evaluated booking for Botox", status: "info" }
                  ].map((act, idx) => {
                    let dotColor = "bg-brand-champagne";
                    if (act.status === "success") dotColor = "bg-brand-emerald";
                    if (act.status === "warning") dotColor = "bg-brand-rose";
                    if (act.status === "info") dotColor = "bg-blue-500";

                    return (
                      <div key={idx} className="relative pl-5 border-l border-brand-border/40 py-0.5">
                        <span className={`absolute -left-[5px] top-1.5 h-2 w-2 rounded-full ${dotColor}`} />
                        <div className="space-y-0.5">
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="text-zinc-300 font-bold">{act.title}</span>
                            <span className="text-zinc-500 font-mono">{act.time}</span>
                          </div>
                          <p className="text-zinc-400 text-[11px] leading-relaxed">{act.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>
      ) : (
        <div className="flex-1 overflow-y-auto scrollable bg-brand-obsidian p-6 space-y-6">
          {/* HEADER ROW */}
          <div className="flex items-center justify-between pb-4 border-b border-brand-border">
            <div>
              <h2 className="text-xl font-bold text-zinc-100">Control & Analytics Dashboard</h2>
              <p className="text-xs text-zinc-400">Manage business rule parameters and track AI scheduling performance telemetry.</p>
            </div>
            <button
              onClick={fetchAdminAnalytics}
              className="bg-brand-border hover:bg-zinc-800 text-brand-champagne border border-brand-border px-4 py-2 rounded text-xs font-bold transition flex items-center gap-1.5"
            >
              <RefreshCw className={`h-3 w-3 ${isLoadingAnalytics ? "animate-spin" : ""}`} />
              Refresh Dashboard
            </button>
          </div>

          {/* METRIC CARDS ROW */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-brand-slate border border-brand-border p-4 rounded-lg flex flex-col justify-between">
              <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Total Triage Decisions</span>
              <span className="text-3xl font-black text-zinc-100 mt-2 font-mono">{adminAnalytics?.telemetry?.total_requests || 0}</span>
              <span className="text-[10px] text-zinc-500 mt-1 block">Live request logs captured</span>
            </div>
            <div className="bg-brand-slate border border-brand-border p-4 rounded-lg flex flex-col justify-between">
              <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Average Pipeline Latency</span>
              <span className="text-3xl font-black text-brand-emerald mt-2 font-mono">{adminAnalytics?.telemetry?.avg_latency_ms || 0} ms</span>
              <span className="text-[10px] text-zinc-500 mt-1 block">Throughput extraction & rules validation</span>
            </div>
            <div className="bg-brand-slate border border-brand-border p-4 rounded-lg flex flex-col justify-between">
              <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Operational Cost & Tokens</span>
              <span className="text-xl font-bold text-zinc-100 mt-2 font-mono">${adminAnalytics?.telemetry?.total_cost_usd || "0.0000"}</span>
              <span className="text-[9px] text-zinc-500 mt-1 block font-mono">{adminAnalytics?.telemetry?.total_tokens || 0} tokens (Prompt/Completion)</span>
            </div>
            <div className="bg-brand-slate border border-brand-border p-4 rounded-lg flex flex-col justify-between">
              <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Human Override Rate</span>
              <span className="text-3xl font-black text-brand-rose mt-2 font-mono">{adminAnalytics?.overrides?.override_rate_pct || 0}%</span>
              <span className="text-[10px] text-zinc-500 mt-1 block">Total overrides: {adminAnalytics?.overrides?.total_overrides || 0}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* COLUMN 1 & 2: TELEMETRY & OVERRIDES ANALYTICS */}
            <div className="lg:col-span-2 space-y-6">
              {/* Overrides Table */}
              <div className="bg-brand-slate border border-brand-border p-5 rounded-lg">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider">Human Override logs</h3>
                  <span className="text-[10px] bg-brand-border border border-brand-border px-2 py-0.5 rounded text-zinc-400">
                    Latest 10 audits
                  </span>
                </div>
                
                <div className="overflow-x-auto text-xs scrollable">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-brand-border text-zinc-500 text-[10px] uppercase font-bold">
                        <th className="py-2 pr-2">Timestamp</th>
                        <th className="py-2 px-2">Patient</th>
                        <th className="py-2 px-2">Override Type</th>
                        <th className="py-2 px-2">Reason Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-brand-border/40">
                      {!adminAnalytics?.overrides?.raw_overrides || adminAnalytics.overrides.raw_overrides.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-8 text-center text-zinc-500 text-xs">
                            No human overrides recorded yet.
                          </td>
                        </tr>
                      ) : (
                        adminAnalytics.overrides.raw_overrides.map((ov: any, index: number) => {
                          const time = ov.timestamp ? new Date(ov.timestamp).toLocaleTimeString() : "";
                          const date = ov.timestamp ? new Date(ov.timestamp).toLocaleDateString([], { month: "short", day: "numeric" }) : "";
                          
                          let typeBadge = "Manual Action";
                          if (ov.difference?.provider_changed && ov.difference?.start_time_changed) {
                            typeBadge = "Provider & Time";
                          } else if (ov.difference?.provider_changed) {
                            typeBadge = "Provider Override";
                          } else if (ov.difference?.start_time_changed) {
                            typeBadge = "Time Override";
                          }
                          
                          return (
                            <tr key={index} className="hover:bg-brand-obsidian/30">
                              <td className="py-2.5 pr-2 font-mono text-[10px] text-zinc-500">
                                {date} {time}
                              </td>
                              <td className="py-2.5 px-2 font-bold text-zinc-300">
                                {ov.patient_id}
                              </td>
                              <td className="py-2.5 px-2">
                                <span className="bg-brand-border px-2 py-0.5 rounded text-[9px] border border-brand-border font-bold text-brand-champagne">
                                  {typeBadge}
                                </span>
                              </td>
                              <td className="py-2.5 px-2 text-zinc-400 truncate max-w-[200px]">
                                {ov.override_reason}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Override Analytics & Performance Details Card */}
              <div className="bg-brand-slate border border-brand-border p-5 rounded-lg">
                <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-4">Override Analysis & Outcome Distribution</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Common Reasons List */}
                  <div className="bg-brand-obsidian/45 border border-brand-border/60 p-3.5 rounded-lg">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-2">Common Override Reasons</span>
                    <div className="space-y-2">
                      {!adminAnalytics?.overrides?.common_reasons || adminAnalytics.overrides.common_reasons.length === 0 ? (
                        <span className="text-[10px] text-zinc-500">No override trends analyzed yet.</span>
                      ) : (
                        adminAnalytics.overrides.common_reasons.map((r: any, idx: number) => (
                          <div key={idx} className="flex justify-between items-center text-[11px]">
                            <span className="text-zinc-300 truncate max-w-[150px]" title={r.reason}>{r.reason}</span>
                            <span className="bg-brand-champagne/10 text-brand-champagne border border-brand-champagne/20 px-1.5 py-0.5 rounded font-mono font-bold text-[9px]">{r.count}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Outcome Distribution List */}
                  <div className="bg-brand-obsidian/45 border border-brand-border/60 p-3.5 rounded-lg">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-2">Outcome Distribution</span>
                    <div className="space-y-2">
                      {adminAnalytics?.telemetry?.outcome_distribution ? (
                        Object.entries(adminAnalytics.telemetry.outcome_distribution).map(([outcome, count]: any) => (
                          <div key={outcome} className="flex justify-between items-center text-[11px]">
                            <span className="text-zinc-400 capitalize">{outcome.replace(/_/g, " ")}</span>
                            <span className="bg-brand-border text-zinc-300 border border-brand-border px-1.5 py-0.5 rounded font-mono font-bold text-[9px]">{count}</span>
                          </div>
                        ))
                      ) : (
                        <span className="text-[10px] text-zinc-500">No outcomes recorded.</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Evaluation harness suite dashboard card */}
              <div className="bg-brand-slate border border-brand-border p-5 rounded-lg">
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-brand-champagne" />
                    <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider">Regression Test Evaluation harness</h3>
                  </div>
                  <button
                    disabled={isRunningEvals}
                    onClick={runEvalsSuite}
                    className="bg-brand-emerald hover:bg-brand-emerald/90 text-zinc-950 px-3 py-1 rounded text-[10px] font-bold transition flex items-center gap-1"
                  >
                    <RefreshCw className={`h-2.5 w-2.5 ${isRunningEvals ? "animate-spin" : ""}`} />
                    Run Evals Suite
                  </button>
                </div>
                
                {evalsResult ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-4 bg-brand-obsidian border border-brand-border p-4 rounded-lg">
                      <div className="text-center border-r border-brand-border pr-6">
                        <span className="text-[10px] text-zinc-500 uppercase block font-bold">Accuracy Score</span>
                        <span className="text-3xl font-black text-brand-emerald font-mono mt-1 block">
                          {evalsResult.score_pct}%
                        </span>
                      </div>
                      <div className="flex-1 text-xs text-zinc-400">
                        <p className="font-semibold text-zinc-200">Suite Passed: {evalsResult.passed}/{evalsResult.total} cases</p>
                        <p className="mt-1">Ensures scheduling assertions, Clinical Safety, VIP exceptions, and prompt injections are verified.</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {evalsResult.categories && Object.keys(evalsResult.categories).map((catName) => {
                        const list = evalsResult.categories[catName];
                        const passed = list.filter((c: any) => c.passed).length;
                        const total = list.length;
                        const score = Math.round(passed / total * 100);
                        return (
                          <div key={catName} className="bg-brand-obsidian/45 border border-brand-border/60 p-2.5 rounded text-[11px]">
                            <div className="flex justify-between font-bold text-zinc-300 uppercase text-[9px] mb-1">
                              <span className="truncate max-w-[80px]">{catName}</span>
                              <span className={score === 100 ? "text-brand-emerald" : "text-brand-champagne"}>{score}%</span>
                            </div>
                            <div className="w-full bg-zinc-800 h-1 rounded-full overflow-hidden">
                              <div className={`h-full ${score === 100 ? "bg-brand-emerald" : "bg-brand-champagne"}`} style={{ width: `${score}%` }}></div>
                            </div>
                            <span className="text-[9px] text-zinc-500 mt-1 block">{passed}/{total} cases</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-zinc-500 py-6 text-xs bg-brand-obsidian/20 rounded border border-dashed border-brand-border">
                    No active evaluation reports loaded. Click "Run Evals Suite" to execute.
                  </div>
                )}
              </div>
            </div>

            {/* COLUMN 3: CONFIGURATION CENTER */}
            <div className="bg-brand-slate border border-brand-border p-5 rounded-lg flex flex-col justify-between">
              <div>
                <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-4 flex items-center gap-1.5">
                  <Database className="h-4 w-4 text-brand-champagne" /> Dynamic Configuration Center
                </h3>
                
                <div className="space-y-4 text-xs">
                  <div>
                    <label className="text-zinc-400 block mb-1 font-bold">Confidence Escalation Threshold</label>
                    <div className="flex items-center gap-3">
                      <input 
                        type="range" 
                        min="0.50" 
                        max="1.00" 
                        step="0.05"
                        value={adminConfig.confidence_threshold} 
                        onChange={(e) => setAdminConfig({...adminConfig, confidence_threshold: parseFloat(e.target.value)})}
                        className="flex-1 accent-brand-champagne"
                      />
                      <span className="font-mono text-zinc-300 font-bold bg-brand-obsidian px-2 py-0.5 rounded border border-brand-border">
                        {adminConfig.confidence_threshold}
                      </span>
                    </div>
                    <span className="text-[10px] text-zinc-500 mt-1 block">
                      Escalate proposed bookings below this confidence value.
                    </span>
                  </div>

                  <div>
                    <label className="text-zinc-400 block mb-1 font-bold">Alternative Slots Count</label>
                    <select
                      value={adminConfig.alternative_slot_count}
                      onChange={(e) => setAdminConfig({...adminConfig, alternative_slot_count: parseInt(e.target.value)})}
                      className="w-full bg-brand-obsidian border border-brand-border rounded px-3 py-2 text-zinc-300 focus:outline-none focus:border-brand-champagne"
                    >
                      <option value={1}>1 Option</option>
                      <option value={2}>2 Options</option>
                      <option value={3}>3 Options</option>
                      <option value={4}>4 Options</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between py-2 border-y border-brand-border/60">
                    <div>
                      <span className="text-zinc-400 block font-bold">Fallback Model Toggle</span>
                      <span className="text-[10px] text-zinc-500 block">Switch to secondary models if main is congested</span>
                    </div>
                    <input 
                      type="checkbox" 
                      checked={adminConfig.fallback_model_enabled}
                      onChange={(e) => setAdminConfig({...adminConfig, fallback_model_enabled: e.target.checked})}
                      className="h-4 w-4 accent-brand-champagne"
                    />
                  </div>

                  <div className="space-y-2">
                    <span className="text-zinc-400 block font-bold uppercase text-[10px] tracking-wider font-bold">Slot Ranker Score Weights</span>
                    
                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-zinc-500">Preferred Provider Weight</span>
                        <span className="font-mono text-zinc-300">{adminConfig.weight_preferred_provider}</span>
                      </div>
                      <input 
                        type="range" 
                        min="0" 
                        max="50" 
                        step="5"
                        value={adminConfig.weight_preferred_provider} 
                        onChange={(e) => setAdminConfig({...adminConfig, weight_preferred_provider: parseFloat(e.target.value)})}
                        className="w-full accent-brand-champagne"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-zinc-500">Back-To-Back Optimization Weight</span>
                        <span className="font-mono text-zinc-300">{adminConfig.weight_back_to_back}</span>
                      </div>
                      <input 
                        type="range" 
                        min="0" 
                        max="50" 
                        step="5"
                        value={adminConfig.weight_back_to_back} 
                        onChange={(e) => setAdminConfig({...adminConfig, weight_back_to_back: parseFloat(e.target.value)})}
                        className="w-full accent-brand-champagne"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-zinc-500">Soonest Slot Penalty (Per day)</span>
                        <span className="font-mono text-zinc-300">{adminConfig.weight_soonest_penalty}</span>
                      </div>
                      <input 
                        type="range" 
                        min="0.0" 
                        max="5.0" 
                        step="0.5"
                        value={adminConfig.weight_soonest_penalty} 
                        onChange={(e) => setAdminConfig({...adminConfig, weight_soonest_penalty: parseFloat(e.target.value)})}
                        className="w-full accent-brand-champagne"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <button
                disabled={isSavingConfig}
                onClick={() => saveAdminConfig(adminConfig)}
                className="mt-6 bg-brand-champagne hover:bg-brand-champagne/90 text-zinc-950 font-bold w-full py-2.5 rounded text-xs transition flex items-center justify-center gap-1.5"
              >
                <Database className="h-4 w-4" />
                {isSavingConfig ? "Saving Settings..." : "Save Settings System-Wide"}
              </button>

              {/* LIVE SYSTEM HEALTH MONITOR */}
              <div className="bg-brand-obsidian/45 border border-brand-border/60 p-4 rounded-lg mt-6 space-y-3">
                <div className="flex justify-between items-center pb-2 border-b border-brand-border">
                  <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-brand-emerald animate-pulse" /> Live System Health
                  </h4>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                    systemHealth?.status === "healthy" ? "bg-brand-emerald/10 text-brand-emerald" : "bg-brand-rose/10 text-brand-rose"
                  }`}>
                    {systemHealth?.status || "HEALTHY"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                  <div className="bg-brand-slate border border-brand-border/40 p-2 rounded flex flex-col">
                    <span className="text-zinc-500 text-[9px] uppercase font-bold tracking-wider">Database</span>
                    <span className="text-brand-emerald mt-1 font-bold">✔ Online</span>
                  </div>
                  <div className="bg-brand-slate border border-brand-border/40 p-2 rounded flex flex-col">
                    <span className="text-zinc-500 text-[9px] uppercase font-bold tracking-wider">API Gate</span>
                    <span className="text-brand-emerald mt-1 font-bold">✔ Active</span>
                  </div>
                  <div className="bg-brand-slate border border-brand-border/40 p-2 rounded flex flex-col">
                    <span className="text-zinc-500 text-[9px] uppercase font-bold tracking-wider">LLM Provider</span>
                    <span className="text-brand-emerald mt-1 font-bold">✔ Operational</span>
                  </div>
                  <div className="bg-brand-slate border border-brand-border/40 p-2 rounded flex flex-col">
                    <span className="text-zinc-500 text-[9px] uppercase font-bold tracking-wider">Background</span>
                    <span className="text-brand-emerald mt-1 font-bold">✔ Connected</span>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* STAFF AI ASSISTANT SLIDING PANEL */}
      {isAskAiOpen && (
        <div className="fixed top-0 right-0 h-full w-96 bg-brand-slate border-l border-brand-border z-50 flex flex-col shadow-2xl animate-fade-in">
          <div className="p-4 border-b border-brand-border flex justify-between items-center bg-brand-obsidian">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-brand-champagne" />
              <h3 className="font-bold text-zinc-100 text-sm">Staff AI Assistant</h3>
            </div>
            <button 
              onClick={() => setIsAskAiOpen(false)}
              className="text-zinc-500 hover:text-zinc-355 hover:bg-zinc-800 px-2 py-1 rounded text-xs font-semibold"
            >
              Close
            </button>
          </div>
          
          {/* Question feed */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollable">
            {!selectedCase ? (
              <div className="text-zinc-500 text-center py-10 text-xs">
                Please select a case to ask questions.
              </div>
            ) : askAiHistory.length === 0 ? (
              <div className="space-y-4">
                <p className="text-xs text-zinc-400">
                  Ask any question about the current case: <strong>{selectedCase.note}</strong>. I cannot book or override, but I can explain the AI's logic.
                </p>
                <div className="space-y-1.5">
                  <span className="text-[10px] text-zinc-500 block uppercase font-bold">Suggested Questions:</span>
                  {getSuggestedQuestions().map(q => (
                    <button
                      key={q}
                      onClick={() => {
                        setAskAiQuestion(q);
                      }}
                      className="w-full text-left bg-brand-obsidian/50 hover:bg-brand-obsidian border border-brand-border p-2 rounded text-xs text-zinc-300 block transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {askAiHistory.map((h, i) => (
                  <div key={i} className="space-y-1.5">
                    <div className={`flex ${h.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`p-3 rounded-lg max-w-[85%] text-xs leading-relaxed space-y-2 ${
                        h.role === 'user' 
                          ? 'bg-brand-champagne/10 border border-brand-champagne/30 text-zinc-100 font-medium' 
                          : 'bg-brand-obsidian border border-brand-border text-zinc-300'
                      }`}>
                        <div>{h.text}</div>
                        {h.role === 'assistant' && (h.groundedConfidence || (h.sources && h.sources.length > 0)) && (
                          <div className="pt-2 border-t border-brand-border/30 flex flex-wrap items-center gap-2 text-[9px] text-zinc-500 font-medium">
                            {h.groundedConfidence && (
                              <span className="text-emerald-500 flex items-center gap-0.5">
                                ✔ Grounded: {h.groundedConfidence}
                              </span>
                            )}
                            {h.sources && h.sources.map((src, sidx) => (
                              <span key={sidx} className="px-1.5 py-0.5 bg-zinc-800 border border-brand-border rounded text-zinc-400 font-mono">
                                {src}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    {h.role === 'assistant' && h.richCards && h.richCards.length > 0 && (
                      <div className="pl-4 space-y-2 max-w-[85%] w-full">
                        {h.richCards.map((card, cidx) => {
                          if (card.type === "schedule_card") {
                            return (
                              <div key={cidx} className="bg-brand-slate/40 border border-brand-border rounded-lg p-3 text-xs space-y-2">
                                <div className="flex justify-between items-center text-[10px] text-zinc-400 uppercase font-bold tracking-wider">
                                  <span>📅 {card.data.provider_name} Schedule</span>
                                  <span>{card.data.date}</span>
                                </div>
                                {card.data.slots && card.data.slots.length > 0 ? (
                                  <div className="flex flex-wrap gap-1.5 mt-1">
                                    {card.data.slots.map((slot: any, sidx: number) => {
                                      const slotStr = typeof slot === "string" ? slot : slot.start || slot.time || "Slot";
                                      return (
                                        <div key={sidx} className="px-2 py-1 rounded bg-brand-obsidian border border-brand-border text-[10px] text-zinc-300">
                                          {slotStr}
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <div className="text-[10px] text-zinc-500 italic">No slots available.</div>
                                )}
                              </div>
                            );
                          }
                          if (card.type === "provider_card") {
                            return (
                              <div key={cidx} className="bg-brand-slate/40 border border-brand-border rounded-lg p-3 text-xs space-y-2">
                                <div className="font-bold text-brand-champagne">{card.data.name}</div>
                                {card.data.specialties && card.data.specialties.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {card.data.specialties.map((spec: string, sidx: number) => (
                                      <span key={sidx} className="bg-zinc-800 text-zinc-300 text-[9px] px-1.5 py-0.5 rounded border border-zinc-700">
                                        {spec}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                {card.data.hours && (
                                  <div className="text-[10px] text-zinc-500 font-mono mt-1">
                                    Working Hours: {JSON.stringify(card.data.hours)}
                                  </div>
                                )}
                              </div>
                            );
                          }
                          if (card.type === "analytics_card") {
                            return (
                              <div key={cidx} className="bg-brand-slate/40 border border-brand-border rounded-lg p-3 text-xs space-y-2">
                                <div className="font-semibold text-zinc-300 text-[10px] uppercase tracking-wider">📊 Analytics Report</div>
                                <div className="grid grid-cols-2 gap-2 mt-1">
                                  {Object.entries(card.data).map(([key, val]: any, sidx) => (
                                    <div key={sidx} className="bg-brand-obsidian/60 p-2 rounded border border-brand-border/40 text-[10px]">
                                      <div className="text-zinc-500 uppercase tracking-tight text-[8px]">{key.replace(/_/g, " ")}</div>
                                      <div className="text-zinc-200 font-bold mt-0.5">{typeof val === "number" ? val.toFixed(1) : String(val)}</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          }
                          return null;
                        })}
                      </div>
                    )}
                    {h.role === 'assistant' && h.toolCalls && h.toolCalls.length > 0 && (
                      <div className="pl-4 flex justify-start">
                        <div className="bg-brand-slate/40 border border-brand-border/60 rounded p-2.5 max-w-[85%] text-[10px] space-y-1 text-zinc-400 w-full">
                          <div className="font-semibold text-zinc-500 uppercase tracking-wider text-[8px]">Tool Execution Logs:</div>
                          {h.toolCalls.map((tc, idx) => (
                            <div key={idx} className="border-b border-brand-border/30 pb-1 last:border-0 last:pb-0">
                              <div className="flex items-center justify-between text-zinc-300">
                                <span>🛠 <strong>{tc.tool}</strong></span>
                                <span className="font-mono text-zinc-500 text-[8px]">{tc.duration_ms}ms</span>
                              </div>
                              <div className="text-zinc-500 truncate text-[9px] mt-0.5" title={tc.observation_preview}>
                                Obs: {tc.observation_preview}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {isAskAiLoading && (
              <div className="flex justify-start animate-pulse">
                <div className="bg-brand-obsidian border border-brand-border p-3 rounded-lg flex items-center gap-2">
                  <div className="h-3 w-3 border-2 border-brand-champagne border-t-transparent rounded-full animate-spin"></div>
                  <span className="text-[10px] text-zinc-500">Formulating explanation...</span>
                </div>
              </div>
            )}
          </div>
          
          {/* Input bar */}
          <form 
            onSubmit={(e) => {
              e.preventDefault();
              handleAskAi();
            }} 
            className="p-3 border-t border-brand-border bg-brand-obsidian flex gap-2"
          >
            <input
              type="text"
              placeholder={selectedCase ? "Ask about this case..." : "Select a case first"}
              disabled={!selectedCase || isAskAiLoading}
              value={askAiQuestion}
              onChange={(e) => setAskAiQuestion(e.target.value)}
              className="flex-1 bg-brand-slate border border-brand-border rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-brand-champagne"
            />
            <button
              type="submit"
              disabled={!selectedCase || isAskAiLoading || !askAiQuestion.trim()}
              className="bg-brand-champagne hover:bg-brand-champagne/95 disabled:opacity-50 text-zinc-950 font-bold px-3 py-1.5 rounded text-xs transition"
            >
              Ask
            </button>
          </form>
        </div>
      )}

      {/* DECISION PIPELINE REPLAY MODAL */}
      {isReplayModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-brand-slate border border-brand-border rounded-lg max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl animate-fade-in">
            <div className="p-4 border-b border-brand-border flex justify-between items-center bg-brand-obsidian rounded-t-lg">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-brand-champagne" />
                <h3 className="font-bold text-zinc-100 text-sm">Decision Pipeline Replay</h3>
              </div>
              <button 
                onClick={() => {
                  setIsReplayModalOpen(false);
                  setSelectedReplayStageIndex(-1);
                }}
                className="text-zinc-400 hover:text-zinc-200 text-xs font-semibold px-2 py-1 rounded hover:bg-zinc-800"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollable">
              {!decideResult || !decideResult.event_stream || decideResult.event_stream.length === 0 ? (
                <div className="text-center text-zinc-500 py-10 text-xs">
                  No pipeline events captured. Run a new decision first.
                </div>
              ) : (
                <div className="relative border-l border-brand-border pl-6 ml-3 space-y-6">
                  {decideResult.event_stream.map((ev, i) => {
                    const startedTime = ev.started_at ? new Date(ev.started_at * 1000).toLocaleTimeString([], { hour12: false }) : "";
                    const isFinished = ev.status === "finished";
                    const isFailed = ev.status === "failed";
                    
                    let dotColor = "bg-brand-champagne";
                    if (isFinished) dotColor = "bg-brand-emerald";
                    if (isFailed) dotColor = "bg-brand-rose";

                    return (
                      <div key={i} className="relative">
                        {/* Timeline dot */}
                        <span className={`absolute -left-[31px] top-1.5 h-3.5 w-3.5 rounded-full border border-brand-slate flex items-center justify-center ${dotColor}`}>
                          {isFinished && <Check className="h-2.5 w-2.5 text-zinc-950" />}
                        </span>
                        
                        <div className={`p-3.5 rounded-lg border transition-all duration-300 ${
                          selectedReplayStageIndex === i 
                            ? "bg-brand-champagne/10 border-brand-champagne ring-1 ring-brand-champagne/30" 
                            : "bg-brand-obsidian/45 border-brand-border"
                        }`}>
                          <div className="flex items-center justify-between gap-3 mb-1.5 flex-wrap">
                            <span className="font-bold text-zinc-200 text-xs uppercase tracking-wider">{ev.stage_name}</span>
                            <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-mono">
                              <span>{startedTime}</span>
                              <span>•</span>
                              <span className="text-zinc-400 font-semibold">{ev.duration_ms.toFixed(1)} ms</span>
                            </div>
                          </div>

                          <div className="space-y-1 text-xs text-zinc-400 leading-relaxed font-mono">
                            {ev.metadata?.model && (
                              <div><span className="text-zinc-500">Model:</span> <span className="text-brand-champagne">{ev.metadata.model}</span></div>
                            )}
                            {ev.metadata?.api_provider && (
                              <div><span className="text-zinc-500">Provider:</span> <span>{ev.metadata.api_provider}</span></div>
                            )}
                            {ev.metadata?.intent && (
                              <div><span className="text-zinc-500">Classified Intent:</span> <span className="text-zinc-300 font-bold">{ev.metadata.intent}</span></div>
                            )}
                            {ev.metadata?.resolved_service_id && (
                              <div><span className="text-zinc-500">Service:</span> <span>{ev.metadata.resolved_service_id}</span></div>
                            )}
                            {ev.metadata?.resolved_provider_id && (
                              <div><span className="text-zinc-500">Provider Match:</span> <span>{ev.metadata.resolved_provider_id}</span></div>
                            )}
                            {ev.metadata?.violated_rules && ev.metadata.violated_rules.length > 0 && (
                              <div>
                                <span className="text-zinc-500">Violated Rules:</span>{" "}
                                <span className="text-brand-rose">{ev.metadata.violated_rules.join(", ")}</span>
                              </div>
                            )}
                            {ev.metadata?.candidate_slots_count !== undefined && (
                              <div><span className="text-zinc-500">Candidate Slots:</span> <span>{ev.metadata.candidate_slots_count} found</span></div>
                            )}
                            {/* Detailed raw payload display */}
                            {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                              <details className="mt-2 text-[10px]">
                                <summary className="cursor-pointer text-zinc-500 hover:text-zinc-400 select-none">View metadata schema</summary>
                                <pre className="mt-1 bg-brand-slate p-2 rounded border border-brand-border text-zinc-400 overflow-x-auto text-[9px] max-h-40 scrollable">
                                  {JSON.stringify(ev.metadata, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Floating Ask AI button in bottom-right */}
      <button
        onClick={() => setIsAskAiOpen(true)}
        className="fixed bottom-6 right-6 z-40 bg-brand-slate border border-brand-border hover:border-brand-champagne text-brand-champagne px-4 py-2.5 rounded-full text-xs font-bold flex items-center gap-2 shadow-2xl transition hover:scale-105"
      >
        <Sparkles className="h-4 w-4" />
        Ask AI Explainer
      </button>

      {/* Toast Alert popover - positioned bottom-left to avoid Ask AI button overlay */}
      {toastMessage && (
        <div className="fixed bottom-6 left-6 bg-brand-slate border border-brand-border text-zinc-100 px-5 py-3 rounded-lg flex items-center gap-3 shadow-2xl z-50 animate-fade-in border-l-4 border-l-brand-champagne">
          <CheckCircle className="h-5 w-5 text-brand-champagne" />
          <span className="text-xs font-semibold">{toastMessage}</span>
        </div>
      )}

      {bookingWorkflowStep >= 0 && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-brand-slate border border-brand-border rounded-lg max-w-md w-full p-6 text-center shadow-2xl animate-fade-in">
            <Sparkles className="h-8 w-8 text-brand-champagne mx-auto mb-3 animate-pulse" />
            <h4 className="font-bold text-zinc-100 text-sm uppercase tracking-wider mb-4">Processing Booking Request</h4>
            
            <div className="space-y-3.5 text-left max-w-xs mx-auto">
              {[
                { label: "Saving Appointment to CRM Database", step: 0 },
                { label: "Generating PDF Treatment Plan Receipt", step: 1 },
                { label: "Dispatching Confirmation Email", step: 2 },
                { label: "Broadcasting Confirmation SMS to Patient", step: 3 },
                { label: "Creating Calendar ICS Invitation", step: 4 }
              ].map((item) => {
                const isActive = bookingWorkflowStep === item.step;
                const isCompleted = bookingWorkflowStep > item.step;
                
                return (
                  <div key={item.step} className="flex items-center gap-3">
                    <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold border transition ${
                      isCompleted 
                        ? "bg-emerald-950 text-brand-emerald border-emerald-800" 
                        : isActive 
                        ? "bg-brand-champagne/10 text-brand-champagne border-brand-champagne animate-pulse" 
                        : "bg-zinc-900/30 text-zinc-600 border-zinc-800"
                    }`}>
                      {isCompleted ? "✔" : isActive ? "●" : "○"}
                    </div>
                    <span className={`text-xs font-semibold ${
                      isCompleted ? "text-zinc-400 line-through" : isActive ? "text-brand-champagne font-bold" : "text-zinc-500"
                    }`}>
                      {item.label}
                    </span>
                  </div>
                );
              })}
            </div>
            
            {bookingWorkflowStep === 5 && (
              <div className="mt-6 text-brand-emerald font-bold text-xs animate-bounce">
                🎉 All tasks completed successfully!
              </div>
            )}
          </div>
        </div>
      )}

      {isCommandPaletteOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-start justify-center p-4 pt-20">
          <div className="bg-brand-slate border border-brand-border rounded-lg max-w-xl w-full flex flex-col shadow-2xl animate-fade-in overflow-hidden">
            <div className="p-3 border-b border-brand-border bg-brand-obsidian flex items-center gap-2">
              <span className="text-zinc-500 text-sm">🔍</span>
              <input
                autoFocus
                type="text"
                value={commandSearchQuery}
                onChange={(e) => setCommandSearchQuery(e.target.value)}
                placeholder="Search patients, providers, services or shortcuts (e.g. Jordan, Sarah, Botox)..."
                className="bg-transparent border-0 outline-0 text-zinc-100 text-xs w-full placeholder-zinc-500"
              />
              <span className="text-[10px] bg-brand-border text-zinc-400 px-1.5 py-0.5 rounded font-mono">ESC</span>
            </div>

            <div className="max-h-[350px] overflow-y-auto p-2 space-y-3 scrollable">
              {!commandSearchQuery && (
                <div className="p-4 space-y-2.5">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Quick Commands</div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-zinc-300">
                    {[
                      { label: "Switch to Admin Dashboard", action: () => { setCurrentView("admin"); setIsCommandPaletteOpen(false); } },
                      { label: "Switch to Operator Panel", action: () => { setCurrentView("operator"); setIsCommandPaletteOpen(false); } },
                      { label: "Filter Today's VIP Patients", action: () => { setSearchQuery("VIP"); setIsCommandPaletteOpen(false); } },
                      { label: "Filter Escalated Reviews", action: () => { setSearchQuery("escalate"); setIsCommandPaletteOpen(false); } },
                      { label: "Open Simulation Sandbox", action: () => { setIsSimulatorOpen(true); setIsCommandPaletteOpen(false); } }
                    ].map((cmd, idx) => (
                      <button
                        key={idx}
                        onClick={cmd.action}
                        className="p-2 text-left bg-brand-slate/80 border border-brand-border rounded hover:border-brand-champagne hover:bg-brand-obsidian transition text-xs font-semibold"
                      >
                        {cmd.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {commandSearchQuery && (
                <div className="space-y-3">
                  {commandSearchResults.patients && commandSearchResults.patients.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[9px] text-zinc-500 uppercase font-bold px-2">Patients</div>
                      {commandSearchResults.patients.map((p) => (
                        <div
                          key={p.id}
                          onClick={() => {
                            setSearchQuery(p.name);
                            setIsCommandPaletteOpen(false);
                            triggerToast(`Filtering case list by patient: ${p.name}`);
                          }}
                          className="flex justify-between items-center p-2 rounded hover:bg-brand-obsidian/60 cursor-pointer text-xs font-medium border border-transparent hover:border-brand-border/40 transition"
                        >
                          <span className="text-zinc-200">{p.name} {p.vip && <span className="text-[9px] bg-brand-champagne/10 text-brand-champagne px-1 rounded ml-1">VIP</span>}</span>
                          <span className="text-zinc-500 font-mono text-[10px]">{p.phone || p.email}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {commandSearchResults.providers && commandSearchResults.providers.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[9px] text-zinc-500 uppercase font-bold px-2">Providers</div>
                      {commandSearchResults.providers.map((prov) => (
                        <div
                          key={prov.id}
                          onClick={() => {
                            setEditedProviderId(prov.id);
                            setIsCommandPaletteOpen(false);
                            triggerToast(`Selected provider: ${prov.name}`);
                          }}
                          className="flex justify-between items-center p-2 rounded hover:bg-brand-obsidian/60 cursor-pointer text-xs font-medium border border-transparent hover:border-brand-border/40 transition"
                        >
                          <span className="text-zinc-200">{prov.name}</span>
                          <span className="text-zinc-500 text-[10px]">{prov.specialties.join(", ")}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {commandSearchResults.services && commandSearchResults.services.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[9px] text-zinc-500 uppercase font-bold px-2">Services</div>
                      {commandSearchResults.services.map((s) => (
                        <div
                          key={s.id}
                          onClick={() => {
                            setSearchQuery(s.name);
                            setIsCommandPaletteOpen(false);
                            triggerToast(`Searching for service: ${s.name}`);
                          }}
                          className="flex justify-between items-center p-2 rounded hover:bg-brand-obsidian/60 cursor-pointer text-xs font-medium border border-transparent hover:border-brand-border/40 transition"
                        >
                          <span className="text-zinc-200">{s.name}</span>
                          <span className="text-zinc-400 font-bold">${s.price_usd}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {!commandSearchResults.patients.length && !commandSearchResults.providers.length && !commandSearchResults.services.length && (
                    <div className="text-center text-zinc-500 py-6 text-xs italic">
                      No matching records found.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <SimulatorPanel 
        isOpen={isSimulatorOpen} 
        onClose={() => setIsSimulatorOpen(false)} 
        onSimulationSent={fetchMessages} 
      />
    </div>
  );
}
