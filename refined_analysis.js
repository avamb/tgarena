#!/usr/bin/env node

const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

const dbPath = path.join(__dirname, 'features.db');
const db = new Database(dbPath, { readonly: true });

// Get all non-passing features
const stmt = db.prepare(`
  SELECT id, priority, category, name, description, steps, passes, in_progress
  FROM features
  WHERE passes = 0
  ORDER BY priority
`);

const allFeatures = stmt.all();

console.log(`Total non-passing features: ${allFeatures.length}`);
console.log('');

// More comprehensive filtering
const excludeKeywords = [
  // Telegram-specific
  'telegram', 'bot', '/start', 'deep link', 'inline', 'keyboard', 'chat',

  // Bill24-specific
  'bill24', 'bill 24', 'create_user', 'get_all_actions', 'external api',

  // WebApp/Widget testing (requires Telegram WebApp context)
  'webapp', 'web app', 'widget',

  // Payment-specific (requires payment provider)
  'payment', 'purchase', 'pay',

  // Notification-specific (requires Telegram)
  'notification', 'notify',

  // User interaction in Telegram
  'click', 'button', 'navigate', 'carousel', 'view event'
];

// Categories that are likely admin/backend features
const adminBackendCategories = ['data', 'cascade', 'error'];

// Analyze each feature
const results = {
  adminBackend: [],
  redis: [],
  backgroundJobs: [],
  dataModel: [],
  otherPotential: []
};

for (const feature of allFeatures) {
  const text = (feature.name + ' ' + feature.description).toLowerCase();
  const hasExcluded = excludeKeywords.some(kw => text.includes(kw));

  if (hasExcluded) {
    continue; // Skip features with excluded keywords
  }

  // Categorize truly implementable features
  if (text.includes('redis') || text.includes('cache') || text.includes('caching')) {
    results.redis.push(feature);
  } else if (text.includes('background') || text.includes('job') || text.includes('queue') || text.includes('arq')) {
    results.backgroundJobs.push(feature);
  } else if (feature.category === 'data' || text.includes('persist') || text.includes('storage') || text.includes('retrieval')) {
    results.dataModel.push(feature);
  } else if (feature.category === 'cascade' || feature.category === 'error') {
    results.adminBackend.push(feature);
  } else {
    results.otherPotential.push(feature);
  }
}

console.log('FEATURES THAT CAN BE IMPLEMENTED WITHOUT EXTERNAL INTEGRATIONS');
console.log('='.repeat(80));
console.log('');

// Print Redis features
if (results.redis.length > 0) {
  console.log('REDIS CACHING FEATURES:');
  console.log('-'.repeat(80));
  results.redis.forEach(f => {
    console.log(`ID ${f.id}: ${f.name}`);
    console.log(`   Description: ${f.description}`);
    console.log(`   Category: ${f.category} | Priority: ${f.priority}`);
    console.log('');
  });
}

// Print Background Job features
if (results.backgroundJobs.length > 0) {
  console.log('BACKGROUND JOB FEATURES:');
  console.log('-'.repeat(80));
  results.backgroundJobs.forEach(f => {
    console.log(`ID ${f.id}: ${f.name}`);
    console.log(`   Description: ${f.description}`);
    console.log(`   Category: ${f.category} | Priority: ${f.priority}`);
    console.log('');
  });
}

// Print Data Model features
if (results.dataModel.length > 0) {
  console.log('DATA MODEL / PERSISTENCE FEATURES:');
  console.log('-'.repeat(80));
  results.dataModel.forEach(f => {
    console.log(`ID ${f.id}: ${f.name}`);
    console.log(`   Description: ${f.description}`);
    console.log(`   Category: ${f.category} | Priority: ${f.priority}`);
    console.log('');
  });
}

// Print Admin/Backend features
if (results.adminBackend.length > 0) {
  console.log('ADMIN PANEL / BACKEND FEATURES:');
  console.log('-'.repeat(80));
  results.adminBackend.forEach(f => {
    console.log(`ID ${f.id}: ${f.name}`);
    console.log(`   Description: ${f.description}`);
    console.log(`   Category: ${f.category} | Priority: ${f.priority}`);
    console.log('');
  });
}

// Print other potential features
if (results.otherPotential.length > 0) {
  console.log('OTHER POTENTIAL FEATURES (NEED REVIEW):');
  console.log('-'.repeat(80));
  results.otherPotential.forEach(f => {
    console.log(`ID ${f.id}: ${f.name}`);
    console.log(`   Description: ${f.description}`);
    console.log(`   Category: ${f.category} | Priority: ${f.priority}`);
    console.log('');
  });
}

// Summary
const totalImplementable = results.redis.length + results.backgroundJobs.length +
                          results.dataModel.length + results.adminBackend.length +
                          results.otherPotential.length;

console.log('');
console.log('='.repeat(80));
console.log('SUMMARY');
console.log('='.repeat(80));
console.log(`Total non-passing features: ${allFeatures.length}`);
console.log(`Features requiring external integrations: ${allFeatures.length - totalImplementable}`);
console.log(`Features that can be implemented: ${totalImplementable}`);
console.log('');
console.log(`  - Redis caching: ${results.redis.length}`);
console.log(`  - Background jobs: ${results.backgroundJobs.length}`);
console.log(`  - Data model: ${results.dataModel.length}`);
console.log(`  - Admin/Backend: ${results.adminBackend.length}`);
console.log(`  - Other (needs review): ${results.otherPotential.length}`);

// Save detailed results
const output = {
  summary: {
    total_non_passing: allFeatures.length,
    total_implementable: totalImplementable,
    by_category: {
      redis: results.redis.length,
      background_jobs: results.backgroundJobs.length,
      data_model: results.dataModel.length,
      admin_backend: results.adminBackend.length,
      other: results.otherPotential.length
    }
  },
  features: results
};

fs.writeFileSync('implementable_features_refined.json', JSON.stringify(output, null, 2));
console.log('');
console.log('Detailed results saved to: implementable_features_refined.json');

db.close();
