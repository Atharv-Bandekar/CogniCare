// frontend/src/types/index.ts

/**
 * Global application settings persisted in localStorage
 */
export interface AppSettings {
  language: string;
  fontSize: "normal" | "large" | "xl";
  voiceSpeed: number;
  highContrast: boolean;
}

/**
 * Props for the Dashboard feature tab
 */
export interface DashboardTabProps {
  session: any;
}

/**
 * Props for the Settings layout sidebar
 */
export interface SettingsSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  updateSetting: (key: keyof AppSettings, value: any) => void;
  language: string;
  session: any;
}