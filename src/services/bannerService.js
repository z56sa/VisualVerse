import axios from 'axios';

const PIXABAY_URL = 'https://pixabay.com/api/';
const MIN_BANNER_RATIO = 1.7;

/**
 * خريطة كلمات البحث: تحدد نوع الصورة المناسب لكل موضوع
 * photo = صور حقيقية | illustration = رسوم/أنمي/فن رقمي | all = الاثنان
 */
const CATEGORY_MAP = {
  // أنمي وفن رقمي → illustration
  anime: 'illustration',
  manga: 'illustration',
  'demon slayer': 'illustration',
  naruto: 'illustration',
  'one piece': 'illustration',
  genshin: 'illustration',
  'jujutsu kaisen': 'illustration',
  art: 'illustration',
  digital: 'illustration',
  fantasy: 'illustration',
  aesthetic: 'illustration',
  lofi: 'illustration',
  cyberpunk: 'illustration',
  retrowave: 'illustration',
  pixel: 'illustration',
  cartoon: 'illustration',
  gaming: 'illustration',
  // طبيعة ومناظر → photo
  nature: 'photo',
  landscape: 'photo',
  sky: 'photo',
  ocean: 'photo',
  mountain: 'photo',
  city: 'photo',
};

/**
 * يحدد نوع الصورة المناسب بناءً على كلمة البحث
 * @param {string} query
 * @returns {'photo' | 'illustration' | 'all'}
 */
function detectImageType(query) {
  const lower = query.toLowerCase();
  for (const [keyword, type] of Object.entries(CATEGORY_MAP)) {
    if (lower.includes(keyword)) return type;
  }
  return 'all'; // الافتراضي: كل الأنواع
}

/**
 * مكتبة بانرات جمالية احتياطية
 */
const CURATED_THEMES = [
  { q: 'anime landscape banner', type: 'illustration' },
  { q: 'cyberpunk city banner', type: 'illustration' },
  { q: 'lofi aesthetic art', type: 'illustration' },
  { q: 'fantasy landscape art', type: 'illustration' },
  { q: 'retrowave synthwave banner', type: 'illustration' },
  { q: 'japanese art landscape', type: 'illustration' },
  { q: 'space galaxy art', type: 'illustration' },
  { q: 'pixel art landscape', type: 'illustration' },
];

function pickRandom(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

function isWideBanner(width, height) {
  if (!width || !height || height <= 0) return false;
  return (width / height) >= MIN_BANNER_RATIO;
}

function formatBanner(hit, displayTerm, source) {
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

/**
 * البحث في Pixabay مع randomPage لمنع التكرار
 * @param {string} apiKey
 * @param {string} query
 * @param {'photo'|'illustration'|'all'} imageType
 */
async function searchPixabay(apiKey, query, imageType = 'all') {
  // أولاً نحصل على عدد النتائج الكلي
  const firstRes = await axios.get(PIXABAY_URL, {
    params: {
      key: apiKey,
      q: query,
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
  const maxPage = Math.min(Math.ceil(totalHits / 50), 6); // حد أقصى 6 صفحات

  // اختر صفحة عشوائية لمنع تكرار نفس النتائج
  const randomPage = maxPage > 1 ? Math.floor(Math.random() * maxPage) + 1 : 1;

  let hits = firstRes.data?.hits || [];

  // إذا الصفحة مختلفة، اجلب الصفحة العشوائية
  if (randomPage > 1) {
    const randomRes = await axios.get(PIXABAY_URL, {
      params: {
        key: apiKey,
        q: query,
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

  // فلترة البانرات العريضة فقط
  return hits.filter(hit => isWideBanner(hit.imageWidth, hit.imageHeight));
}

export async function getSurpriseBanner(apiKey) {
  const theme = pickRandom(CURATED_THEMES);
  try {
    const results = await searchPixabay(apiKey, theme.q, theme.type);
    if (results.length > 0) return formatBanner(pickRandom(results), theme.q, 'surprise');
  } catch (e) {
    console.warn('[Surprise] Failed:', e.message);
  }
  return getSmartBanner(apiKey, 'anime landscape', true);
}

export async function getSmartBanner(apiKey, query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'anime';
  const imageType = detectImageType(rawTerm);

  // صياغة استعلامات بحث متخصصة
  const queries = [
    { q: `${rawTerm} banner landscape`, type: imageType },
    { q: `${rawTerm} wallpaper wide`, type: imageType },
    { q: rawTerm, type: imageType },
  ];

  for (const { q, type } of queries) {
    try {
      const results = await searchPixabay(apiKey, q, type);
      if (results.length > 0) {
        return formatBanner(pickRandom(results), rawTerm, isSurprise ? 'surprise' : 'search');
      }
    } catch (err) {
      console.warn(`[Pixabay] Failed for "${q}":`, err.message);
    }
  }

  // بحث احتياطي من المكتبة المُنسقة
  for (const theme of CURATED_THEMES.slice(0, 3)) {
    try {
      const results = await searchPixabay(apiKey, theme.q, theme.type);
      if (results.length > 0) {
        return formatBanner(pickRandom(results), theme.q, 'fallback');
      }
    } catch (e) {
      console.warn('[Fallback] Failed:', e.message);
    }
  }

  // بانر طوارئ موثوق
  return {
    id: 'emergency',
    title: 'Anime Aesthetic Landscape Banner',
    url: 'https://cdn.pixabay.com/photo/2024/02/15/14/43/ai-generated-8576400_1280.jpg',
    pageUrl: 'https://pixabay.com',
    dimensions: '1280x720',
    ratio: '1.78',
    source: 'emergency_fallback',
    displayTerm: rawTerm
  };
}
