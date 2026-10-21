import axios from 'axios';

/**
 * Minimum aspect ratio for wide/landscape banners
 * width / height >= 1.7 → only real horizontal banners accepted
 */
const MIN_BANNER_RATIO = 1.7;

/**
 * Curated fallback banner themes when primary search returns no wide images
 */
const CURATED_FALLBACKS = [
  'anime discord banner header',
  'cyberpunk discord banner header',
  'lofi aesthetic discord header',
  'retrowave discord banner',
  'aesthetic landscape discord header',
  'gaming discord banner header',
  'dark aesthetic discord banner'
];

/**
 * Picks a random item from an array
 * @param {Array} arr 
 * @returns {*}
 */
function pickRandom(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * فحص صارم للأبعاد: نرفض أي صورة عرضها / ارتفاعها < 1.7
 * @param {{ width: number, height: number }} dims 
 * @returns {boolean}
 */
function isWideBanner({ width, height }) {
  if (!width || !height || height <= 0) return false;
  return (width / height) >= MIN_BANNER_RATIO;
}

/**
 * دالة السحب الأساسية من Pinterest
 * نستخدم نقطة نهاية البحث المخفية الخاصة بـ Pinterest التي تعيد JSON
 * @param {string} query - كلمة البحث
 * @param {number} batchSize - عدد النتائج
 * @returns {Promise<Array>}
 */
async function fetchPinterestResults(query, batchSize = 50) {
  const searchUrl = 'https://www.pinterest.com/resource/BaseSearchResource/get/';

  const params = {
    source_url: `/search/pins/?q=${encodeURIComponent(query)}&rs=typed`,
    data: JSON.stringify({
      options: {
        query,
        scope: 'pins',
        page_size: batchSize,
        bookmarks: []
      },
      context: {}
    }),
    _: Date.now()
  };

  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': `https://www.pinterest.com/search/pins/?q=${encodeURIComponent(query)}`,
    'X-Pinterest-AppState': 'active',
    'X-App-Version': '1.0.0',
    'DNT': '1'
  };

  const response = await axios.get(searchUrl, {
    params,
    headers,
    timeout: 10000
  });

  // استخرج النتائج من هيكل بيانات Pinterest
  const data = response.data?.resource_response?.data?.results;
  if (!Array.isArray(data)) return [];

  return data;
}

/**
 * تحويل نتيجة Pinterest إلى هيكل بانر قياسي موحّد
 * @param {Object} pin 
 * @param {string} displayTerm 
 * @param {string} source 
 * @returns {Object}
 */
function formatPinterestBanner(pin, displayTerm, source) {
  // Pinterest يحتوي على عدة صيغ للصورة مرتبة من الأعلى جودة إلى الأدنى
  const imageData = pin.images?.orig ||
                    pin.images?.['736x'] ||
                    pin.images?.['564x'] ||
                    pin.images?.['236x'];

  const url = imageData?.url || pin.image?.url;
  const width = imageData?.width || pin.image?.width || 0;
  const height = imageData?.height || pin.image?.height || 0;
  const title = pin.title || pin.description || pin.alt_text || 'Discord Animated Banner';

  return {
    id: pin.id || 'unknown',
    title: title.substring(0, 250),
    url,
    pinterestUrl: `https://www.pinterest.com/pin/${pin.id}/`,
    dimensions: `${Math.round(width)}x${Math.round(height)}`,
    ratio: height > 0 ? (width / height).toFixed(2) : 'Wide',
    source,
    displayTerm
  };
}

/**
 * جلب بانر مفاجئ عشوائي
 * @returns {Promise<Object>}
 */
export async function getSurpriseBanner() {
  const randomTheme = pickRandom(CURATED_FALLBACKS);
  return getSmartBanner(randomTheme, true);
}

/**
 * المحرك الرئيسي للبحث عن البانرات العريضة من Pinterest
 * @param {string} query - كلمة بحث المستخدم
 * @param {boolean} isSurprise 
 * @returns {Promise<Object>}
 */
export async function getSmartBanner(query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'anime';

  // صياغة كلمات البحث المتخصصة في هيدرات وبانرات ديسكورد
  const searchQueries = rawTerm.toLowerCase().includes('banner') || rawTerm.toLowerCase().includes('header')
    ? [rawTerm, `${rawTerm} discord`, `${rawTerm} aesthetic wide`]
    : [
        `${rawTerm} discord banner header`,
        `${rawTerm} banner landscape`,
        `${rawTerm} discord header aesthetic`
      ];

  // محاولة جلب وفلترة النتائج من Pinterest
  for (const q of searchQueries) {
    try {
      const results = await fetchPinterestResults(q, 50);

      if (results.length > 0) {
        // فلترة صارمة: نرفض أي صورة بنسبة عرض/ارتفاع < 1.7
        const wideBanners = results.filter(pin => {
          const imageData = pin.images?.orig || pin.images?.['736x'];
          const width = imageData?.width || 0;
          const height = imageData?.height || 1;
          return isWideBanner({ width, height });
        });

        if (wideBanners.length > 0) {
          const selected = pickRandom(wideBanners);
          return formatPinterestBanner(selected, rawTerm, isSurprise ? 'surprise' : 'pinterest_search');
        }
      }
    } catch (err) {
      console.warn(`[Pinterest] Query failed for "${q}":`, err.message);
    }
  }

  // بانر احتياطي من المكتبة المُنسقة إذا لم تعمل نتائج Pinterest
  for (const fallbackQ of CURATED_FALLBACKS.slice(0, 3)) {
    try {
      const results = await fetchPinterestResults(fallbackQ, 30);
      const wideBanners = results.filter(pin => {
        const imageData = pin.images?.orig || pin.images?.['736x'];
        const width = imageData?.width || 0;
        const height = imageData?.height || 1;
        return isWideBanner({ width, height });
      });

      if (wideBanners.length > 0) {
        const selected = pickRandom(wideBanners);
        return formatPinterestBanner(
          selected,
          fallbackQ.replace(' discord banner header', ''),
          'fallback'
        );
      }
    } catch (e) {
      console.warn(`[Pinterest] Fallback query failed:`, e.message);
    }
  }

  // بانر طوارئ في حال توقف Pinterest عن الاستجابة
  return {
    id: 'emergency-banner',
    title: 'Aesthetic Cyberpunk Wide Banner',
    url: 'https://i.pinimg.com/originals/84/86/5d/84865d16fce1a1e63c6d5f9d2f5e76ea.jpg',
    pinterestUrl: 'https://www.pinterest.com',
    dimensions: '1920x500',
    ratio: '3.84',
    source: 'emergency_fallback',
    displayTerm: rawTerm
  };
}
