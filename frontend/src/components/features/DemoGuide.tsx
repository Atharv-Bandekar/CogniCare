"use client";

import { useState, useEffect } from "react";

interface DemoGuideProps {
  isOpen: boolean;
  onClose: () => void;
}

const steps = [
  {
    title: "Create an Elder Profile",
    description:
      'Click "Add Elder via Telegram" to create a profile for the person you want to monitor. Give them a name, pick a language (English, Hindi, Marathi, or Tamil), and set a preferred time.',
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    svgPath: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="8.5" cy="7" r="4" />
        <line x1="20" y1="8" x2="20" y2="14" />
        <line x1="23" y1="11" x2="17" y2="11" />
      </>
    ),
  },
  {
    title: "Share the Telegram Link",
    description:
      "After creating the elder, you'll get a deep-link. Share this link with the elder — when they tap it, their Telegram account gets linked to CogniCare automatically.",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    svgPath: (
      <>
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </>
    ),
  },
  {
    title: "Elder Answers Daily Questions",
    description:
      "The AI asks a daily memory question in the elder's language via Telegram. They reply with text or a voice note. Each answer is analyzed for sentiment, engagement, and cognitive signals.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    svgPath: (
      <>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </>
    ),
  },
  {
    title: "Track Insights on the Dashboard",
    description:
      "Back here on the dashboard, you can see the full interaction history, sentiment trends, engagement levels, and weekly reports — all updated in real-time as the elder responds.",
    color: "text-cyan-400",
    bg: "bg-cyan-500/10",
    svgPath: (
      <>
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </>
    ),
  },
  {
    title: "Act on AI Recommendations",
    description:
      "The system generates personalized activity recommendations (call the elder, plan a visit, suggest an exercise). Mark them done, dismiss them, or send a custom message directly to the elder's Telegram.",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    svgPath: (
      <>
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </>
    ),
  },
];

export default function DemoGuide({ isOpen, onClose }: DemoGuideProps) {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (isOpen) setCurrentStep(0);
  }, [isOpen]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3">
          <div>
            <h3 className="text-lg font-bold text-slate-100">Quick Start Guide</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Step {currentStep + 1} of {steps.length}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors p-1"
            aria-label="Close guide"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Progress bar */}
        <div className="px-6">
          <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Step content */}
        <div className="px-6 py-8">
          <div className={`w-14 h-14 rounded-2xl ${step.bg} flex items-center justify-center mb-5`}>
            <svg className={`h-7 w-7 ${step.color}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              {step.svgPath}
            </svg>
          </div>
          <h4 className="text-xl font-bold text-slate-100 mb-3">{step.title}</h4>
          <p className="text-sm text-slate-400 leading-relaxed">{step.description}</p>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between px-6 pb-5">
          <button
            onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
            disabled={currentStep === 0}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Back
          </button>

          <div className="flex gap-1.5">
            {steps.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentStep(i)}
                className={`h-2 rounded-full transition-all ${
                  i === currentStep
                    ? "w-6 bg-blue-500"
                    : "w-2 bg-slate-700 hover:bg-slate-600"
                }`}
                aria-label={`Go to step ${i + 1}`}
              />
            ))}
          </div>

          {isLast ? (
            <button
              onClick={onClose}
              className="flex items-center gap-1.5 text-sm font-semibold text-blue-400 hover:text-blue-300 transition-colors"
            >
              Get Started
              <span className="text-lg">→</span>
            </button>
          ) : (
            <button
              onClick={() => setCurrentStep((s) => s + 1)}
              className="flex items-center gap-1.5 text-sm font-medium text-slate-300 hover:text-slate-100 transition-colors"
            >
              Next
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
