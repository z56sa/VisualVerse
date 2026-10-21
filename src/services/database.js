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
    title: 'Neon Cyberpunk Samurai',
    category: 'anime',
    avatar_url: 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=1024&q=80',
    banner_url: 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=1024&q=80',
    source: 'Default Gallery',
    created_at: new Date().toISOString()
  },
  {
    id: 2,
    title: 'Cozy Sunset Couple',
    category: 'couples',
    avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1024&q=80',
    banner_url: 'https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=1024&q=80',
    source: 'Default Gallery',
    created_at: new Date().toISOString()
  },
  {
    id: 3,
    title: 'Dark Minimalist Aesthetic',
    category: 'aesthetic',
    avatar_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1024&q=80',
    banner_url: 'https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=1024&q=80',
    source: 'Default Gallery',
    created_at: new Date().toISOString()
  },
  {
    id: 4,
    title: 'Ethereal Cosmic Fantasy',
    category: 'gaming',
    avatar_url: 'https://images.unsplash.com/photo-1563089145-599997674d42?w=1024&q=80',
    banner_url: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1024&q=80',
    source: 'Default Gallery',
    created_at: new Date().toISOString()
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
        this.pairs = JSON.parse(raw);
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

  addPair({ title, category, avatar_url, banner_url, source }) {
    const nextId = this.pairs.length > 0 ? Math.max(...this.pairs.map(p => p.id)) + 1 : 1;
    const newRecord = {
      id: nextId,
      title,
      category: category.toLowerCase().trim(),
      avatar_url,
      banner_url,
      source: source || 'Admin',
      created_at: new Date().toISOString()
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
      filtered = filtered.filter(p => p.id !== excludeId);
    }

    if (filtered.length === 0) {
      return null;
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
