import axios from 'axios';

const PIXABAY_URL = 'https://pixabay.com/api/';

/**
 * نسبة أبعاد البانر الصارمة: عرض / ارتفاع >= 1.7
 */
const MIN_BANNER_RATIO = 1.7;

/**
 * مكتبة موضوعات بانر جمالية احتياطية
 */
const CURATED_BANNER_THEMES = [
  'anime landscape',
  'cyberpunk city',
  'lofi aesthetic',
  'retrowave synthwave',
  'japanese aesthetic',
  'dark fantasy landscape',
  'space galaxy',
  'pixel art landscape',
  'aesthetic nature',
  'gaming wallpaper'
];

/**
 * اختيار عنصر عشوائي من مصفوفة
 */
function pickRandom(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * فحص نسبة الأبعاد الصارمة (>= 1.7) لقبول البانرات العريضة فقط
 */
function isWideBanner(width, height) {
  if (!width || !height || height <= 0) return false;
  return (width / height) >= MIN_BANNER_RATIO;
}

/**
 * تنسيق نتيجة Pixabay كهيكل بانر قياسي
 */
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
 * البحث في Pixabay مع فلترة صارمة للبانرات العريضة
 */
async function searchPixabay(apiKey, query, page = 1) {
  const response = await axios.get(PIXABAY_URL, {
    params: {
      key: apiKey,
      q: query,
      image_type: 'photo',
      orientation: 'horizontal', // أفقي فقط
      per_page: 50,
      page,
      safesearch: true,
      order: 'popular'
    },
    timeout: 8000
  });

  const hits = response.data?.hits;
  if (!Array.isArray(hits) || hits.length === 0) return [];

  // فلترة صارمة: عرض / ارتفاع >= 1.7
  return hits.filter(hit =>
    isWideBanner(hit.imageWidth, hit.imageHeight)
  );
}

/**
 * جلب بانر مفاجئ عشوائي
 */
export async function getSurpriseBanner(apiKey) {
  const theme = pickRandom(CURATED_BANNER_THEMES);
  return getSmartBanner(apiKey, theme, true);
}

/**
 * المحرك الرئيسي: بحث وفلترة البانرات العريضة من Pixabay
 */
export async function getSmartBanner(apiKey, query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'anime';

  // صياغات بحث متخصصة في الخلفيات العريضة
  const queries = rawTerm.toLowerCase().includes('banner') || rawTerm.toLowerCase().includes('landscape')
    ? [rawTerm, `${rawTerm} wallpaper`]
    : [`${rawTerm} landscape wallpaper`, `${rawTerm} banner background`, rawTerm];

  for (const q of queries) {
    try {
      const page = Math.floor(Math.random() * 3) + 1; // صفحات عشوائية لتنويع النتائج
      const results = await searchPixabay(apiKey, q, page);
      if (results.length > 0) {
        return formatBanner(pickRandom(results), rawTerm, isSurprise ? 'surprise' : 'search');
      }
    } catch (err) {
      console.warn(`[Pixabay] Query failed for "${q}":`, err.message);
    }
  }

  // بحث احتياطي من المكتبة المُنسقة
  for (const theme of CURATED_BANNER_THEMES.slice(0, 4)) {
    try {
      const results = await searchPixabay(apiKey, theme);
      if (results.length > 0) {
        return formatBanner(pickRandom(results), theme, 'fallback');
      }
    } catch (e) {
      console.warn('[Pixabay] Fallback search error:', e.message);
    }
  }

  // بانر طوارئ موثوق
  return {
    id: 'emergency',
    title: 'Aesthetic Landscape Banner',
    url: 'https://cdn.pixabay.com/photo/2022/01/11/21/48/background-6931101_1280.jpg',
    pageUrl: 'https://pixabay.com',
    dimensions: '1280x500',
    ratio: '2.56',
    source: 'emergency_fallback',
    displayTerm: rawTerm
  };
}
