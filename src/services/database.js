import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Ensure data folder exists
const dataDir = path.resolve(__dirname, '../../data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbPath = path.join(dataDir, 'visualverse.sqlite');
const db = new Database(dbPath);

// Enable WAL mode for performance & concurrent reads
db.pragma('journal_mode = WAL');

// Initialize tables
db.exec(`
  CREATE TABLE IF NOT EXISTS matching_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    avatar_url TEXT NOT NULL,
    banner_url TEXT NOT NULL,
    source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE INDEX IF NOT EXISTS idx_category ON matching_pairs(category);
`);

// Seed default sample data if table is empty
const countStmt = db.prepare('SELECT COUNT(*) AS total FROM matching_pairs');
const { total } = countStmt.get();

if (total === 0) {
  const insertStmt = db.prepare(`
    INSERT INTO matching_pairs (title, category, avatar_url, banner_url, source)
    VALUES (@title, @category, @avatar_url, @banner_url, @source)
  `);

  const initialSeed = [
    {
      title: 'Neon Cyberpunk Samurai',
      category: 'anime',
      avatar_url: 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=1024&q=80',
      banner_url: 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=1024&q=80',
      source: 'Default Gallery'
    },
    {
      title: 'Cozy Sunset Couple',
      category: 'couples',
      avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1024&q=80',
      banner_url: 'https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=1024&q=80',
      source: 'Default Gallery'
    },
    {
      title: 'Dark Minimalist Aesthetic',
      category: 'aesthetic',
      avatar_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1024&q=80',
      banner_url: 'https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=1024&q=80',
      source: 'Default Gallery'
    },
    {
      title: 'Ethereal Cosmic Fantasy',
      category: 'gaming',
      avatar_url: 'https://images.unsplash.com/photo-1563089145-599997674d42?w=1024&q=80',
      banner_url: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1024&q=80',
      source: 'Default Gallery'
    }
  ];

  const seedTransaction = db.transaction((items) => {
    for (const item of items) {
      insertStmt.run(item);
    }
  });

  seedTransaction(initialSeed);
}

export const dbService = {
  /**
   * Add a new matching pair
   */
  addPair({ title, category, avatar_url, banner_url, source }) {
    const stmt = db.prepare(`
      INSERT INTO matching_pairs (title, category, avatar_url, banner_url, source)
      VALUES (?, ?, ?, ?, ?)
    `);
    const result = stmt.run(title, category.toLowerCase(), avatar_url, banner_url, source || 'Admin');
    return { id: result.lastInsertRowid };
  },

  /**
   * Get random matching pair by category or any category
   */
  getRandomPair(category = null, excludeId = null) {
    let query = 'SELECT * FROM matching_pairs WHERE 1=1';
    const params = [];

    if (category && category !== 'all') {
      query += ' AND category = ?';
      params.push(category.toLowerCase());
    }

    if (excludeId) {
      query += ' AND id != ?';
      params.push(excludeId);
    }

    query += ' ORDER BY RANDOM() LIMIT 1';

    let row = db.prepare(query).get(...params);

    // If excluding ID returned empty (e.g. only 1 item in category), get without excludeId
    if (!row && excludeId) {
      query = 'SELECT * FROM matching_pairs WHERE 1=1';
      const fallbackParams = [];
      if (category && category !== 'all') {
        query += ' AND category = ?';
        fallbackParams.push(category.toLowerCase());
      }
      query += ' ORDER BY RANDOM() LIMIT 1';
      row = db.prepare(query).get(...fallbackParams);
    }

    return row || null;
  },

  /**
   * Get pair by ID
   */
  getPairById(id) {
    const stmt = db.prepare('SELECT * FROM matching_pairs WHERE id = ?');
    return stmt.get(id);
  },

  /**
   * Get total count and categories statistics
   */
  getStats() {
    const totalStmt = db.prepare('SELECT COUNT(*) AS total FROM matching_pairs');
    const categoriesStmt = db.prepare(`
      SELECT category, COUNT(*) as count 
      FROM matching_pairs 
      GROUP BY category 
      ORDER BY count DESC
    `);
    return {
      total: totalStmt.get().total,
      categories: categoriesStmt.all()
    };
  },

  /**
   * Delete a matching pair by ID
   */
  deletePair(id) {
    const stmt = db.prepare('DELETE FROM matching_pairs WHERE id = ?');
    const result = stmt.run(id);
    return result.changes > 0;
  }
};

export default dbService;
