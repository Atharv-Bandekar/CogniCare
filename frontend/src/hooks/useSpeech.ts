// frontend/src/hooks/useSpeech.ts
import { useEffect } from "react";

export function useSpeech(language: string) {
  const speakText = (text: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    const langMap: Record<string, string> = {
      "Hindi": "hi-IN", "Marathi": "mr-IN", "Tamil": "ta-IN", "English": "en-US"
    };
    
    const targetLangCode = langMap[language] || "en-US";
    utterance.lang = targetLangCode;
    utterance.rate = 0.9; 

    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = 
      voices.find(v => v.lang === targetLangCode) || 
      voices.find(v => v.lang.startsWith(targetLangCode.split('-')[0])) ||
      voices.find(v => v.name.toLowerCase().includes(language.toLowerCase()));
    
    if (matchingVoice) utterance.voice = matchingVoice;
    window.speechSynthesis.speak(utterance);
  };

  // Browser Hack: Force voice loading into memory on mount
  useEffect(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }
  }, []);

  return { speakText };
}