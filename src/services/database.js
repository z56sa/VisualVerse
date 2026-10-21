import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dataDir = path.resolve(__dirname, '../../data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbFilePath = path.join(dataDir, 'visualverse_data.json');

const defaultSeed = [
  {
    id: 1,
    title: 'Anime Sunset Aesthetic',
    category: 'anime',
    avatarUrl: 'https://th.wallhaven.cc/lg/ly/lygl92.jpg',
    bannerUrl: 'https://w.wallhaven.cc/full/ly/wallhaven-lygl92.png',
    source: 'Wallhaven Anime',
    createdAt: new Date().toISOString()
  },
  {
    id: 2,
    title: 'Romantic Couple Rooftop',
    category: 'couples',
    avatarUrl: 'https://th.wallhaven.cc/orig/yq/yqkgj7.jpg',
    bannerUrl: 'https://w.wallhaven.cc/full/yq/wallhaven-yqkgj7.png',
    source: 'Wallhaven Couples',
    createdAt: new Date().toISOString()
  },
  {
    id: 3,
    title: 'Neon Tokyo Cyberpunk',
    category: 'aesthetic',
    avatarUrl: 'https://th.wallhaven.cc/lg/7j/7jx86v.jpg',
    bannerUrl: 'https://w.wallhaven.cc/full/7j/wallhaven-7jx86v.png',
    source: 'Wallhaven Aesthetic',
    createdAt: new Date().toISOString()
  },
  {
    id: 4,
    title: 'Valorant Reyna & Omen',
    category: 'gaming',
    avatarUrl: 'https://th.wallhaven.cc/lg/6l/6le8rw.jpg',
    bannerUrl: 'https://w.wallhaven.cc/full/6l/wallhaven-6le8rw.jpg',
    source: 'Wallhaven Gaming',
    createdAt: new Date().toISOString()
  }
];

class DatabaseStore {
  constructor() {
    this.pairs = [];
    this._load();
  }

  _load() {
    try {
      if (fs.existsSync(dbFilePath)) {
        const raw = fs.readFileSync(dbFilePath, 'utf8');
        const parsed = JSON.parse(raw);
        // Normalize fields if needed
        this.pairs = parsed.map(item => ({
          id: item.id,
          title: item.title,
          category: (item.category || 'anime').toLowerCase().trim(),
          avatarUrl: item.avatarUrl || item.avatar_url || '',
          bannerUrl: item.bannerUrl || item.banner_url || '',
          source: item.source || 'Admin',
          createdAt: item.createdAt || item.created_at || new Date().toISOString()
        }));
      } else {
        this.pairs = [...defaultSeed];
        this._save();
      }
    } catch (e) {
      console.error('Error loading JSON DB, using seed data:', e);
      this.pairs = [...defaultSeed];
    }
  }

  _save() {
    try {
      fs.writeFileSync(dbFilePath, JSON.stringify(this.pairs, null, 2), 'utf8');
    } catch (e) {
      console.error('Error saving JSON DB:', e);
    }
  }

  addPair({ title, category, avatarUrl, bannerUrl, source }) {
    const nextId = this.pairs.length > 0 ? Math.max(...this.pairs.map(p => p.id)) + 1 : 1;
    const newRecord = {
      id: nextId,
      title: title.trim(),
      category: category.toLowerCase().trim(),
      avatarUrl: (avatarUrl || '').trim(),
      bannerUrl: (bannerUrl || '').trim(),
      source: source || 'Admin',
      createdAt: new Date().toISOString()
    };
    this.pairs.push(newRecord);
    this._save();
    return { id: nextId };
  }

  getRandomPair(category = null, excludeId = null) {
    let filtered = this.pairs;

    if (category && category !== 'all') {
      filtered = filtered.filter(p => p.category === category.toLowerCase().trim());
    }

    if (excludeId && filtered.length > 1) {
      filtered = filtered.filter(p => p.id !== Number(excludeId));
    }

    if (filtered.length === 0) {
      // Fallback: search ignoring category if empty
      filtered = this.pairs;
      if (filtered.length === 0) return null;
    }

    const randomIndex = Math.floor(Math.random() * filtered.length);
    return filtered[randomIndex];
  }

  getPairById(id) {
    return this.pairs.find(p => p.id === Number(id)) || null;
  }

  getStats() {
    const counts = {};
    for (const p of this.pairs) {
      counts[p.category] = (counts[p.category] || 0) + 1;
    }
    const categories = Object.keys(counts).map(cat => ({
      category: cat,
      count: counts[cat]
    }));
    return {
      total: this.pairs.length,
      categories
    };
  }

  deletePair(id) {
    const initialLen = this.pairs.length;
    this.pairs = this.pairs.filter(p => p.id !== Number(id));
    if (this.pairs.length < initialLen) {
      this._save();
      return true;
    }
    return false;
  }
}

export const dbService = new DatabaseStore();
export default dbService;
