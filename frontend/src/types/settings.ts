export interface SettingsProfile {
  name: string;
  skills: string[];
  services: string[];
  hourly_rate: number;
  min_budget: number;
}

export interface SettingsEmail {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  sender_name: string;
  from_email: string;
}

export interface SettingsScraping {
  proxy_url: string | null;
  max_concurrent: number;
}

export interface Settings {
  profile: SettingsProfile;
  email: SettingsEmail;
  scraping: SettingsScraping;
}
