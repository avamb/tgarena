#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Check if better-sqlite3 is available
let Database;
try {
  Database = require('better-sqlite3');
} catch (err) {
  console.log('better-sqlite3 not found. Please install it:');
  console.log('npm install better-sqlite3');
  process.exit(1);
}

const dbPath = path.join(__dirname, 'features.db');

try {
  const db = new Database(dbPath, { readonly: true });

  // Get all non-passing features
  const stmt = db.prepare(`
    SELECT id, priority, category, name, description, passes, in_progress
    FROM features
    WHERE passes = 0
    ORDER BY priority
  `);

  const allFeatures = stmt.all();

  console.log(`Total non-passing features: ${allFeatures.length}`);
  console.log('');

  // Keywords that indicate external integrations
  const telegramKeywords = [
    'telegram', 'bot', '/start', 'deep link', 'message',
    'callback', 'inline', 'keyboard', 'chat', 'send'
  ];

  const bill24Keywords = [
    'bill24', 'api', 'create_user', 'get_all_actions',
    'external api', 'webhook', 'http request', 'bill 24'
  ];

  const implementableFeatures = [];

  for (const feature of allFeatures) {
    const text = (feature.name + ' ' + feature.description).toLowerCase();

    // Check if feature requires external integrations
    const hasTelegram = telegramKeywords.some(kw => text.includes(kw));
    const hasBill24 = bill24Keywords.some(kw => text.includes(kw));

    if (!hasTelegram && !hasBill24) {
      implementableFeatures.push(feature);
    }
  }

  console.log(`Features that can be implemented without external integrations: ${implementableFeatures.length}`);
  console.log('');
  console.log('='.repeat(80));
  console.log('');

  // Print implementable features
  for (const feature of implementableFeatures) {
    console.log(`Feature ID: ${feature.id} (Priority: ${feature.priority})`);
    console.log(`Category: ${feature.category}`);
    console.log(`Name: ${feature.name}`);
    console.log(`Description: ${feature.description}`);
    console.log(`In Progress: ${feature.in_progress ? 'Yes' : 'No'}`);
    console.log('');
    console.log('-'.repeat(80));
    console.log('');
  }

  // Save to JSON file
  const outputPath = path.join(__dirname, 'implementable_features.json');
  fs.writeFileSync(outputPath, JSON.stringify(implementableFeatures, null, 2));

  console.log(`\nSaved to ${outputPath}`);

  db.close();

} catch (err) {
  console.error('Error:', err.message);
  process.exit(1);
}
