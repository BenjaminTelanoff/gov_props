const fs = require('fs');
require('dotenv').config();

const targetPath = './src/environments/environment.ts';

const envConfigFile = `export const environment = {
  production: false,
  firebase: {
    apiKey: '${process.env.NG_APP_FIREBASE_DEV_API_KEY}',
    authDomain: '${process.env.NG_APP_FIREBASE_AUTH_DOMAIN}',
    projectId: '${process.env.NG_APP_FIREBASE_PROJECT_ID}',
    storageBucket: '${process.env.NG_APP_FIREBASE_STORAGE_BUCKET}',
    messagingSenderId: '${process.env.NG_APP_FIREBASE_MESSAGING_SENDER_ID}',
    appId: '${process.env.NG_APP_FIREBASE_APP_ID}',
    measurementId: '${process.env.NG_APP_FIREBASE_MEASUREMENT_ID}'
  }
};`;

fs.writeFileSync(targetPath, envConfigFile);
console.log('✅ Keys injected into environment.ts');