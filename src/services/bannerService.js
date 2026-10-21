import axios from 'axios';

const PIXABAY_URL = 'https://pixabay.com/api/';
const SAFEBOORU_URL = 'https://safebooru.org/index.php';
const MIN_BANNER_RATIO = 1.7;

/**
 * كلمات البحث التي تُوجَّه إلى Safebooru (أنمي حصراً)
 */
const ANIME_KEYWORDS = [
  'anime', 'manga', 'naruto', 'one piece', 'demon slayer', 'kimetsu',
  'attack on titan', 'bleach', 'dragon ball', 'genshin', 'jujutsu',
  'haikyuu', 'mha', 'bnha', 'sword art online', 're zero', 'overlord',
  'fairy tail', 'black clover', 'tokyo ghoul', 'hunter hunter',
  'evangelion', 'cowboy bebop', 'fullmetal', 'chainsaw man',
  'spy family', 'bocchi', 'oshi no ko', 'blue lock', 'vinland',
  'waifu', 'chibi', 'moe', 'shounen', 'shoujo', 'isekai'
];

/**
 * هل الكلمة تخص الأنمي؟
 */
function isAnimeQuery(query) {
  const lower = query.toLowerCase();
  return ANIME_KEYWORDS.some(k => lower.includes(k));
}

function pickRandom(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

function isWideBanner(width, height) {
  if (!width || !height || height <= 0) return false;
  return (width / height) >= MIN_BANNER_RATIO;
}

// ─────────────────────────────────────────────────────────────────────────────
//  SAFEBOORU – للأنمي حصراً (SFW, مجاني، بدون API Key)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * بحث في Safebooru مع فلترة صارمة على الأبعاد
 * نستخدم تاج wide_image + landscape للحصول على بانرات أفقية
 */
async function searchSafebooru(query) {
  // Safebooru tags: نضيف wide_image أو landscape للحصول على بانرات
  const tags = `${query.replace(/ /g, '_')} wide_image`;
  const pid = Math.floor(Math.random() * 5); // تنويع الصفحة لمنع التكرار

  const response = await axios.get(SAFEBOORU_URL, {
    params: {
      page: 'dapi',
      s: 'post',
      q: 'index',
      json: 1,
      tags,
      limit: 50,
      pid
    },
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      'Accept': 'application/json'
    },
    timeout: 10000
  });

  const posts = response.data;
  if (!Array.isArray(posts) || posts.length === 0) {
    // جرب بدون wide_image إذا لم تجد نتائج
    const res2 = await axios.get(SAFEBOORU_URL, {
      params: {
        page: 'dapi',
        s: 'post',
        q: 'index',
        json: 1,
        tags: query.replace(/ /g, '_'),
        limit: 100,
        pid: Math.floor(Math.random() * 10)
      },
      headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json' },
      timeout: 10000
    });
    const posts2 = res2.data;
    if (!Array.isArray(posts2)) return [];
    return posts2.filter(p => p.file_url && isWideBanner(p.width, p.height));
  }

  return posts.filter(p => p.file_url && isWideBanner(p.width, p.height));
}

function formatSafeBooru(post, displayTerm, source) {
  // Safebooru يعطي file_url كـ URL نسبي أو مطلق
  let url = post.file_url;
  if (url && !url.startsWith('http')) {
    url = `https://safebooru.org${url}`;
  }

  return {
    id: String(post.id),
    title: post.tags ? post.tags.split(' ').slice(0, 5).join(', ') : 'Anime Banner',
    url,
    pageUrl: `https://safebooru.org/index.php?page=post&s=view&id=${post.id}`,
    dimensions: `${post.width}x${post.height}`,
    ratio: (post.width / post.height).toFixed(2),
    source,
    displayTerm
  };
}

// ─────────────────────────────────────────────────────────────────────────────
//  PIXABAY – للمحتوى العام (مناظر، جيمنج، فن رقمي غير أنمي)
// ─────────────────────────────────────────────────────────────────────────────

async function searchPixabay(apiKey, query, imageType = 'all') {
  const firstRes = await axios.get(PIXABAY_URL, {
    params: {
      key: apiKey,
      q: `${query} wide landscape`,
      image_type: imageType,
      orientation: 'horizontal',
      per_page: 50,
      page: 1,
      safesearch: true,
      order: 'popular'
    },
    timeout: 8000
  });

  const totalHits = firstRes.data?.totalHits || 0;
  const maxPage = Math.min(Math.ceil(totalHits / 50), 6);
  const randomPage = maxPage > 1 ? Math.floor(Math.random() * maxPage) + 1 : 1;

  let hits = firstRes.data?.hits || [];

  if (randomPage > 1) {
    const randomRes = await axios.get(PIXABAY_URL, {
      params: {
        key: apiKey,
        q: `${query} wide landscape`,
        image_type: imageType,
        orientation: 'horizontal',
        per_page: 50,
        page: randomPage,
        safesearch: true,
        order: 'popular'
      },
      timeout: 8000
    });
    hits = randomRes.data?.hits || hits;
  }

  return hits.filter(h => isWideBanner(h.imageWidth, h.imageHeight));
}

function formatPixabay(hit, displayTerm, source) {
  return {
    id: String(hit.id),
    title: hit.tags ? hit.tags.split(',').slice(0, 4).join(', ') : 'Discord Banner',
    url: hit.largeImageURL || hit.webformatURL,
    pageUrl: hit.pageURL || 'https://pixabay.com',
    dimensions: `${hit.imageWidth}x${hit.imageHeight}`,
    ratio: (hit.imageWidth / hit.imageHeight).toFixed(2),
    source,
    displayTerm
  };
}

// ─────────────────────────────────────────────────────────────────────────────
//  MAIN ENGINE
// ─────────────────────────────────────────────────────────────────────────────

const SURPRISE_ANIME_TAGS = ['scenery', 'landscape', 'city', 'night sky', 'fantasy', 'cherry blossoms'];

export async function getSurpriseBanner(apiKey) {
  // بانر مفاجئ: أنمي عشوائي من Safebooru
  const tag = pickRandom(SURPRISE_ANIME_TAGS);
  try {
    const results = await searchSafebooru(tag);
    if (results.length > 0) return formatSafeBooru(pickRandom(results), tag, 'surprise');
  } catch (e) {
    console.warn('[Surprise Safebooru]', e.message);
  }
  // Pixabay كبديل
  try {
    const results = await searchPixabay(apiKey, 'fantasy landscape');
    if (results.length > 0) return formatPixabay(pickRandom(results), 'surprise', 'surprise');
  } catch (e) {}

  return getEmergencyBanner('surprise');
}

export async function getSmartBanner(apiKey, query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'anime';
  const source = isSurprise ? 'surprise' : 'search';

  // ─── مسار الأنمي: Safebooru ───────────────────────────────────────────────
  if (isAnimeQuery(rawTerm)) {
    // استعلامات متعددة بترتيب أولوية
    const animeTags = [
      rawTerm,
      `${rawTerm} scenery`,
      `${rawTerm} landscape`,
    ];

    for (const tag of animeTags) {
      try {
        const results = await searchSafebooru(tag);
        if (results.length > 0) {
          return formatSafeBooru(pickRandom(results), rawTerm, source);
        }
      } catch (err) {
        console.warn(`[Safebooru] "${tag}" failed:`, err.message);
      }
    }
  }

  // ─── مسار العام: Pixabay ──────────────────────────────────────────────────
  if (apiKey && apiKey.trim().length > 0) {
    const imageType = ['cyberpunk', 'retro', 'pixel', 'digital', 'art', 'fantasy', 'aesthetic']
      .some(k => rawTerm.toLowerCase().includes(k))
      ? 'illustration' : 'all';

    try {
      const results = await searchPixabay(apiKey, rawTerm, imageType);
      if (results.length > 0) return formatPixabay(pickRandom(results), rawTerm, source);
    } catch (err) {
      console.warn('[Pixabay]', err.message);
    }
  }

  // ─── Fallback: Safebooru scenery ──────────────────────────────────────────
  try {
    const results = await searchSafebooru('scenery landscape');
    if (results.length > 0) return formatSafeBooru(pickRandom(results), rawTerm, 'fallback');
  } catch {}

  return getEmergencyBanner(rawTerm);
}

function getEmergencyBanner(term) {
  return {
    id: 'emergency',
    title: 'Anime Scenic Landscape Banner',
    url: 'https://safebooru.org//images/4467/e1a6c9cc7eb6a22c00e35a3d10b4d58e4f0892a5.jpg',
    pageUrl: 'https://safebooru.org',
    dimensions: '1920x1080',
    ratio: '1.78',
    source: 'emergency_fallback',
    displayTerm: term
  };
}
