// Isolated on purpose: our own sw.js keeps scope "/" so offline + auto-update are untouched.
// OneSignal needs its worker; their docs say to put it in a subdirectory for exactly this case.
importScripts("https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.sw.js");
