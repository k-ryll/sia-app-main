// config/api.js
export const API_TOKEN = "beb27169-6302-4af3-b7c3-65865a3eb334";
export const API_CONFIG = {
  BASE_URL: "http://localhost:8000",
  ENDPOINTS: {
    TRANSLATE: "/send",
    MESSAGES: "/messages",
  },
};

export function getApiUrl(endpoint) {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
}
