// frontend/src/components/layout/WelcomeSplash.tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "../ui/Button";

export default function WelcomeSplash() {
  const [isVisible, setIsVisible] = useState(true);
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    const hasSeenSplash = sessionStorage.getItem("cognicare_splash_seen");
    if (hasSeenSplash) {
      setIsVisible(false);
    }
  }, []);

  const handleEnter = () => {
    setIsFadingOut(true);
    sessionStorage.setItem("cognicare_splash_seen", "true");
    setTimeout(() => setIsVisible(false), 500); 
  };

  if (!isVisible) return null;

  return (
    <div className={`fixed inset-0 z-[100] flex flex-col items-center justify-center bg-slate-950 transition-opacity duration-700 ease-in-out ${isFadingOut ? "opacity-0" : "opacity-100"}`}>
      <div className="max-w-lg mx-auto p-8 text-center flex flex-col items-center animate-fade-in">
        
        {/* Animated Logo Container */}
        <div className="relative w-36 h-36 mb-10 flex items-center justify-center">
          {/* 1. The Breathing Glow (Animated) */}
          <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-2xl animate-pulse"></div>
          
          {/* 2. The Core Circle (Static) */}
          <div className="relative w-32 h-32 bg-slate-900 border border-slate-800 rounded-full flex items-center justify-center shadow-2xl">
            {/* 3. The SVG Icon */}
            <svg className="w-16 h-16 text-blue-400 drop-shadow-[0_0_15px_rgba(59,130,246,0.4)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
        </div>

        <h1 className="text-5xl font-extrabold text-white mb-4 tracking-tight">
          CogniCare <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">AI</span>
        </h1>
        
        <p className="text-2xl text-slate-300 mb-14 leading-relaxed">
          Your daily companion for a sharp mind and a great day.
        </p>

        <Button 
          variant="primary" 
          onClick={handleEnter}
          className="text-2xl py-6 px-12 w-full max-w-md shadow-[0_0_30px_rgba(37,99,235,0.2)] hover:shadow-[0_0_40px_rgba(37,99,235,0.4)] transition-all duration-300"
        >
          Tap Here to Begin
        </Button>
      </div>
    </div>
  );
}