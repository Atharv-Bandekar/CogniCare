// frontend/src/hooks/useSettings.ts
import { useState, useEffect } from "react";
import { AppSettings } from "../types"; // Importing from your central types file!

const defaultSettings: AppSettings = {
  language: "English",
  fontSize: "normal",
  voiceSpeed: 0.9,
  highContrast: false,
};

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("cognicare_settings");
    if (saved) {
      try {
        setSettings(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse settings");
      }
    }
    setIsLoaded(true);
  }, []);

  const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => {
      const updated = { ...prev, [key]: value };
      localStorage.setItem("cognicare_settings", JSON.stringify(updated));
      return updated;
    });
  };

  return { settings, updateSetting, isLoaded };
}