import axios from 'axios';

const GIPHY_BASE = 'https://api.giphy.com/v1/gifs';
const TENOR_BASE = 'https://tenor.googleapis.com/v2/search';
const MIN_RATIO = 1.7;

/**
 * قوالب بحث متخصصة للبانرات المتحركة حسب الموضوع
 */
const SEARCH_TEMPLATES = {
  anime: [
    'anime scenery banner gif',
    'anime landscape wide banner',
    'anime banner header animated',
    'anime city night banner gif',
    'anime sunset banner landscape'
  ],
  gaming: [
    'gaming banner gif animated',
    'game intro banner wide',
    'esports banner animated'
  ],
  cyberpunk: [
    'cyberpunk city banner gif',
    'cyberpunk neon banner animated',
    'cyberpunk landscape banner'
  ],
  lofi: [
    'lofi anime banner gif',
    'lofi aesthetic banner animated',
    'lofi city banner landscape'
  ],
  default: [
    '{q} banner animated gif',
    '{q} banner wide landscape',
    '{q} header banner gif'
  ]
};

/**
 * يحدد قائمة الاستعلامات المناسبة للكلمة
 */
function getSearchQueries(query) {
  const lower = query.toLowerCase();
  if (['anime', 'naruto', 'genshin', 'demon', 'one piece', 'bleach', 'manga',
       'jujutsu', 'attack on titan', 'sword art', 'dragon ball'].some(k => lower.includes(k))) {
    return SEARCH_TEMPLATES.anime;
  }
  if (['gaming', 'game', 'fps', 'esport', 'minecraft', 'fortnite'].some(k => lower.includes(k))) {
    return SEARCH_TEMPLATES.gaming;
  }
  if (lower.includes('cyberpunk') || lower.includes('neon')) return SEARCH_TEMPLATES.cyberpunk;
  if (lower.includes('lofi') || lower.includes('lo-fi')) return SEARCH_TEMPLATES.lofi;

  // افتراضي: استبدال {q} بكلمة المستخدم
  return SEARCH_TEMPLATES.default.map(t => t.replace('{q}', query));
}

function pickRandom(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * فحص صارم للأبعاد (>= 1.7) من بيانات Giphy
 */
function isWide(item) {
  const orig = item?.images?.original;
  if (!orig) return false;
  const w = parseFloat(orig.width);
  const h = parseFloat(orig.height);
  if (!w || !h || h <= 0) return false;
  return (w / h) >= MIN_RATIO;
}

function formatGiphy(item, displayTerm, source) {
  const orig = item.images?.original;
  const w = orig?.width || '?';
  const h = orig?.height || '?';
  const ratio = h !== '?' ? (parseFloat(w) / parseFloat(h)).toFixed(2) : '?';
  return {
    id: item.id,
    title: item.title || 'Animated Banner',
    url: orig?.url || item.url,
    pageUrl: item.url || 'https://giphy.com',
    dimensions: `${w}x${h}`,
    ratio,
    source,
    displayTerm,
    animated: true
  };
}

/**
 * بحث في Giphy مع فلترة صارمة وتنويع بالـ offset
 */
async function searchGiphy(apiKey, query, offset = null) {
  const useOffset = offset ?? Math.floor(Math.random() * 25);
  const res = await axios.get(`${GIPHY_BASE}/search`, {
    params: {
      api_key: apiKey,
      q: query,
      limit: 50,
      offset: useOffset,
      rating: 'pg-13',
      lang: 'en'
    },
    timeout: 8000
  });

  const hits = res.data?.data;
  if (!Array.isArray(hits) || hits.length === 0) return [];
  return hits.filter(isWide);
}

// ─────────────────────────────────────────────────────────────────────────────

const SURPRISE_QUERIES = [
  'anime scenery banner gif',
  'anime city night banner',
  'lofi anime banner landscape',
  'cyberpunk banner animated',
  'fantasy landscape banner gif',
  'aesthetic sky banner gif'
];

export async function getSurpriseBanner(apiKey) {
  const q = pickRandom(SURPRISE_QUERIES);
  return getSmartBanner(apiKey, q, true);
}

export async function getSmartBanner(apiKey, query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'anime';
  const source = isSurprise ? 'surprise' : 'search';
  const queries = getSearchQueries(rawTerm);

  // جرب كل قالب بحث بترتيب
  for (const q of queries) {
    try {
      // محاولة بـ offset عشوائي لتنويع النتائج
      let results = await searchGiphy(apiKey, q);
      if (results.length === 0) {
        // إعادة المحاولة بـ offset = 0 إذا لم تجد نتائج
        results = await searchGiphy(apiKey, q, 0);
      }
      if (results.length > 0) {
        return formatGiphy(pickRandom(results), rawTerm, source);
      }
    } catch (err) {
      console.warn(`[Giphy] "${q}" failed:`, err.message);
    }
  }

  // Fallback: بحث مباشر بكلمة المستخدم + banner
  try {
    const results = await searchGiphy(apiKey, `${rawTerm} banner`, 0);
    if (results.length > 0) {
      return formatGiphy(pickRandom(results), rawTerm, 'fallback');
    }
  } catch (e) {
    console.warn('[Giphy fallback]', e.message);
  }

  // Fallback نهائي: أنمي سينري متحرك
  try {
    const results = await searchGiphy(apiKey, 'anime scenery banner', 0);
    if (results.length > 0) {
      return formatGiphy(pickRandom(results), rawTerm, 'fallback');
    }
  } catch {}

  // بانر طوارئ (GIF متحرك موثوق)
  return {
    id: 'emergency',
    title: 'Anime Scenic Banner',
    url: 'https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif',
    pageUrl: 'https://giphy.com',
    dimensions: '500x200',
    ratio: '2.50',
    source: 'emergency_fallback',
    displayTerm: rawTerm,
    animated: true
  };
}
