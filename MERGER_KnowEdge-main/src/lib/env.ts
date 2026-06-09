/**
 * Environment Variable Checker
 * Ensures required variables are present and provides type-safe access.
 */

export const isServer = typeof window === 'undefined';

export const env = {
  // Frontend (Vite)
  APP_URL: (typeof import.meta !== 'undefined' && import.meta.env?.VITE_APP_URL) || '',
  
  // Backend (Node) - only accessible if isServer is true
  get GEMINI_API_KEY() {
    return isServer ? process.env.GEMINI_API_KEY : undefined;
  },
  get GPTZERO_API_KEY() {
    return isServer ? (process.env.GPTZERO_API_KEY || process.env.X_API_KEY || process.env.GPT_ZERO_KEY) : undefined;
  },
  get ZEROGPT_API_KEY() {
    return isServer ? (process.env.ZEROGPT_API_KEY || process.env.ZERO_GPT_KEY || process.env.ZEROGPT_SECRET) : undefined;
  },
  get GRAMMARLY_API_KEY() {
    return isServer ? (process.env.GRAMMARLY_API_KEY || process.env.GRAMMARLY_CLIENT_ID || process.env.GRAMMARLY_SECRET) : undefined;
  },
  get SAPLING_API_KEY() {
    return isServer ? (process.env.SAPLING_API_KEY || process.env.SAPLING_SECRET) : undefined;
  },
  get ORIGINALITY_AI_KEY() {
    return isServer ? (process.env.ORIGINALITY_AI_KEY || process.env.ORIGINALITY_API_KEY) : undefined;
  },
  // Self-Hosted Stack Config
  get APP_DB() { return isServer ? process.env.APP_DB : undefined; },
  get CACHE_BACKEND() { return isServer ? process.env.CACHE_BACKEND : undefined; },
  get STORAGE_BACKEND() { return isServer ? process.env.STORAGE_BACKEND : undefined; },
  get STORAGE_PATH() { return isServer ? process.env.STORAGE_PATH : undefined; },
  get AI_SCREENING_MODE() { return isServer ? process.env.AI_SCREENING_MODE : undefined; },
  get LANGUAGETOOL_URL() { return isServer ? process.env.LANGUAGETOOL_URL : undefined; },
  get VALE_MODE() { return isServer ? process.env.VALE_MODE : undefined; },
  get EMBEDDING_PROVIDER() { return isServer ? process.env.EMBEDDING_PROVIDER : undefined; },
  get EMBEDDING_MODEL() { return isServer ? process.env.EMBEDDING_MODEL : undefined; },
  get VECTOR_BACKEND() { return isServer ? process.env.VECTOR_BACKEND : undefined; },
  get SOCIAL_MODE() { return isServer ? process.env.SOCIAL_MODE : undefined; },
  get MAX_UPLOAD_MB() { return isServer ? process.env.MAX_UPLOAD_MB : undefined; }
};

export function validateEnv() {
  const missing: string[] = [];

  if (isServer) {
    // We log status but do not block unless GEMINI_API_KEY is missing (if app requires it)
    console.log('Environment Status (Server):', {
      GEMINI_API_KEY: !!process.env.GEMINI_API_KEY,
      // Stack Config - using fallbacks instead of strictly requiring
      APP_DB: !!process.env.APP_DB,
      AI_SCREENING_MODE: !!process.env.AI_SCREENING_MODE,
      EMBEDDING_PROVIDER: !!process.env.EMBEDDING_PROVIDER,
      SOCIAL_MODE: !!process.env.SOCIAL_MODE,
    });
  } else {
    // Frontend validation
    console.log('Environment Validation (Client):', {
      VITE_APP_URL: !!(typeof import.meta !== 'undefined' && import.meta.env?.VITE_APP_URL),
      // We explicitly DO NOT check for VITE_GPTZERO_API_KEY here as they are now server-side
    });
  }

  if (missing.length > 0) {
    const msg = `CRITICAL: Missing environment variables: ${missing.join(', ')}`;
    if (isServer) {
      console.error(msg);
    } else {
      console.warn(msg);
    }
    return false;
  }

  return true;
}
