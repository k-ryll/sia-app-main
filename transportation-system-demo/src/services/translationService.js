import { getApiUrl, API_TOKEN } from '../config/api';

class TranslationService {
  constructor() {
    this.apiToken = API_TOKEN; // developer-provided token
  }

  // Internal helper for requests with token
  async request(endpoint, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${this.apiToken}`,
      ...(options.headers || {}),
    };

    const response = await fetch(getApiUrl(endpoint), {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return response.json();
  }

  // Map frontend language codes to backend language codes
  mapLanguageCode(frontendLang) {
    const mapping = {
      tl: "fil",
      en: "en",
      ceb: "ceb",
      ilo: "ilo",
      pag: "pag",
      zh: "zh",
      ja: "ja",
      ko: "ko",
    };
    return mapping[frontendLang] || "en";
  }

  // Save a message
  async saveMessage(text, targetLang = "en") {
    const backendLang = this.mapLanguageCode(targetLang);
    return this.request("/send", {
      method: "POST",
      body: JSON.stringify({ text, target_lang: backendLang }),
    });
  }

  // Get messages
  async getMessages(lang = "en") {
    const backendLang = this.mapLanguageCode(lang);
    return this.request(`/messages?lang=${backendLang}`);
  }
}

export default new TranslationService();
