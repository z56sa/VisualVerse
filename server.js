/*
 * VisualVerse — Matching Avatars & Banners Explorer
 * Express.js Backend Server
 */

const express    = require('express');
const path       = require('path');
const fs         = require('fs');
const cors       = require('cors');
const compression = require('compression');
const helmet     = require('helmet');
const morgan     = require('morgan');

const app  = express();
const PORT = process.env.PORT || 3000;

// ── Middleware ──────────────────────────────────────────────────────────────
app.use(morgan('combined'));
app.use(compression());
app.use(cors());

// Helmet with relaxed CSP to allow Tailwind CDN & external images
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc:  ["'self'", "'unsafe-inline'", 'cdn.tailwindcss.com', 'unpkg.com'],
        styleSrc:   ["'self'", "'unsafe-inline'", 'cdn.tailwindcss.com', 'fonts.googleapis.com', 'unpkg.com'],
        fontSrc:    ["'self'", 'fonts.gstatic.com'],
        imgSrc:     ["'self'", 'data:', 'https:', 'blob:'],
        connectSrc: ["'self'"],
      },
    },
  })
);

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ── Data helpers ────────────────────────────────────────────────────────────
const DATA_PATH = path.join(__dirname, 'data', 'matching.json');

function loadPairs() {
  try {
    const raw = fs.readFileSync(DATA_PATH, 'utf8');
    return JSON.parse(raw);
  } catch (err) {
    console.error('[VisualVerse] Failed to load data:', err.message);
    return [];
  }
}

function savePairs(pairs) {
  fs.writeFileSync(DATA_PATH, JSON.stringify(pairs, null, 2), 'utf8');
}

// ── API Routes ──────────────────────────────────────────────────────────────

/* GET /api/pairs — all pairs, optional ?category= & ?q= filters */
app.get('/api/pairs', (req, res) => {
  let pairs = loadPairs();

  const { category, q } = req.query;

  if (category && category !== 'all') {
    pairs = pairs.filter(p => p.category.toLowerCase() === category.toLowerCase());
  }

  if (q) {
    const query = q.toLowerCase();
    pairs = pairs.filter(p =>
      p.title.toLowerCase().includes(query) ||
      (p.tags || []).some(t => t.toLowerCase().includes(query))
    );
  }

  res.json({ success: true, total: pairs.length, data: pairs });
});

/* GET /api/pairs/random — one random pair, optional ?category= */
app.get('/api/pairs/random', (req, res) => {
  let pairs = loadPairs();

  const { category } = req.query;
  if (category && category !== 'all') {
    pairs = pairs.filter(p => p.category.toLowerCase() === category.toLowerCase());
  }

  if (pairs.length === 0) {
    return res.status(404).json({ success: false, message: 'No pairs found' });
  }

  const random = pairs[Math.floor(Math.random() * pairs.length)];
  res.json({ success: true, data: random });
});

/* GET /api/pairs/:id — single pair by id */
app.get('/api/pairs/:id', (req, res) => {
  const pairs = loadPairs();
  const pair  = pairs.find(p => p.id === req.params.id);
  if (!pair) return res.status(404).json({ success: false, message: 'Pair not found' });
  res.json({ success: true, data: pair });
});

/* GET /api/categories — distinct category list with counts */
app.get('/api/categories', (req, res) => {
  const pairs = loadPairs();
  const map   = {};

  for (const p of pairs) {
    const cat = p.category || 'other';
    map[cat]  = (map[cat] || 0) + 1;
  }

  const categories = [
    { id: 'all',       label: 'All',        icon: '🌐', count: pairs.length },
    { id: 'anime',     label: 'Anime',      icon: '⛩️',  count: map['anime']     || 0 },
    { id: 'gaming',    label: 'Gaming',     icon: '🎮',  count: map['gaming']    || 0 },
    { id: 'couples',   label: 'Couples',    icon: '💞',  count: map['couples']   || 0 },
    { id: 'aesthetic', label: 'Aesthetic',  icon: '✨',  count: map['aesthetic'] || 0 },
  ];

  res.json({ success: true, data: categories });
});

/* POST /api/pairs — add a new pair (admin use) */
app.post('/api/pairs', (req, res) => {
  const { category, title, tags, avatar1, avatar2, banner } = req.body;

  if (!category || !title || !avatar1?.url || !avatar2?.url || !banner?.url) {
    return res.status(400).json({ success: false, message: 'Missing required fields' });
  }

  const pairs = loadPairs();
  const newPair = {
    id: `${category}-${Date.now()}`,
    category,
    title,
    tags: tags || [],
    avatar1,
    avatar2,
    banner,
  };

  pairs.push(newPair);
  savePairs(pairs);

  res.status(201).json({ success: true, data: newPair });
});

/* DELETE /api/pairs/:id — remove a pair */
app.delete('/api/pairs/:id', (req, res) => {
  const pairs   = loadPairs();
  const index   = pairs.findIndex(p => p.id === req.params.id);

  if (index === -1) return res.status(404).json({ success: false, message: 'Pair not found' });

  pairs.splice(index, 1);
  savePairs(pairs);

  res.json({ success: true, message: 'Pair deleted' });
});

/* GET /api/stats — quick dashboard stats */
app.get('/api/stats', (req, res) => {
  const pairs = loadPairs();
  const cats  = [...new Set(pairs.map(p => p.category))];
  res.json({
    success: true,
    data: {
      totalPairs:      pairs.length,
      totalCategories: cats.length,
      categories:      cats,
    },
  });
});

// ── SPA fallback ────────────────────────────────────────────────────────────
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ── Start ───────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🎨  VisualVerse is running on http://localhost:${PORT}`);
  console.log(`📦  Data file: ${DATA_PATH}`);
  console.log(`🚀  Environment: ${process.env.NODE_ENV || 'development'}\n`);
});

module.exports = app;
