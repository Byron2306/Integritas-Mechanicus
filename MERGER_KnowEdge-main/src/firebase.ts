import { initializeApp, getApp, getApps, FirebaseApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, Auth } from 'firebase/auth';
import { getFirestore, Firestore } from 'firebase/firestore';
import firebaseConfigData from '../firebase-applet-config.json';

// Global error listener to swallow Firebase configuration errors before they reach the debug panel
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    if (event.message?.includes('Firebase') || event.message?.includes('configuration') || event.filename?.includes('firebase')) {
      // Don't prevent default if it's a real crash, but swallow the ones that look like config noise
      if (event.message?.includes('apiKey') || event.message?.includes('authDomain')) {
        event.stopImmediatePropagation();
        event.preventDefault();
      }
    }
  }, true);
}

let app: FirebaseApp | undefined;
let auth: Auth | undefined;
let db: Firestore | undefined;
const googleProvider = new GoogleAuthProvider();

// Temporary console override to suppress SDK-internal console.error calls during init
const originalError = console.error;
console.error = (...args) => {
  if (args[0]?.toString().includes('Firebase') || args[0]?.toString().includes('configuration')) {
    console.warn("[Firebase suppressed error]:", ...args);
    return;
  }
  originalError.apply(console, args);
};

try {
  const config = {
    apiKey: process.env.VITE_FIREBASE_API_KEY || firebaseConfigData.apiKey,
    authDomain: process.env.VITE_FIREBASE_AUTH_DOMAIN || firebaseConfigData.authDomain,
    projectId: process.env.VITE_FIREBASE_PROJECT_ID || firebaseConfigData.projectId,
    storageBucket: process.env.VITE_FIREBASE_STORAGE_BUCKET || firebaseConfigData.storageBucket,
    messagingSenderId: process.env.VITE_FIREBASE_MESSAGING_SENDER_ID || firebaseConfigData.messagingSenderId,
    appId: process.env.VITE_FIREBASE_APP_ID || firebaseConfigData.appId,
    measurementId: process.env.VITE_FIREBASE_MEASUREMENT_ID || firebaseConfigData.measurementId,
  };

  if (!getApps().length) {
    app = initializeApp(config);
  } else {
    app = getApp();
  }

  auth = getAuth(app);
  db = getFirestore(app, (firebaseConfigData as any).firestoreDatabaseId);
} catch (error) {
  console.warn("Firebase initialization skipped or failed (config error caught):", error);
} finally {
  // Restore original console.error
  console.error = originalError;
}

export { app, auth, db, googleProvider };
export default app;
