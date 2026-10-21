import axios from 'axios';

const MIN_RATIO = 1.8;

/**
 * User-Agents متنوعة لتقليل احتمال الحظر
 */
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
];

function pickRandom(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * فحص صارم: العرض / الارتفاع >= 1.8
 */
function isWideBanner(width, height) {
  const w = parseFloat(width);
  const h = parseFloat(height);
  if (!w || !h || isNaN(w) || isNaN(h) || h <= 0) return false;
  return (w / h) >= MIN_RATIO;
}

/**
 * استخراج روابط الصور الأصلية من نتائج Pinterest
 * يدعم هيكل البيانات للإصدارات المختلفة من Pinterest API
 */
function extractPins(data) {
  try {
    // المسار الأول: BaseSearchResource
    const results =
      data?.resource_response?.data?.results ||
      data?.resourceResponses?.[0]?.response?.data?.results ||
      [];

    return results
      .filter(pin => pin && (pin.images || pin.image))
      .map(pin => {
        const orig =
          pin.images?.orig ||
          pin.images?.['736x'] ||
          pin.images?.['564x'] ||
          pin.image;

        const width = orig?.width || pin.dominant_color ? null : null;
        const height = orig?.height || null;

        // Fallback للأبعاد من حقل آخر
        const w = pin.images?.orig?.width || pin.images?.['736x']?.width || 0;
        const h = pin.images?.orig?.height || pin.images?.['736x']?.height || 0;

        return {
          id: pin.id,
          url: orig?.url || pin.image?.url,
          width: w,
          height: h,
          title: pin.title || pin.description || '',
          pageUrl: `https://www.pinterest.com/pin/${pin.id}/`
        };
      })
      .filter(p => p.url && p.url.startsWith('http'));
  } catch {
    return [];
  }
}

/**
 * دالة السحب الرئيسية من Pinterest
 * @param {string} query - كلمة البحث مع discord banner header مُضافة تلقائياً
 * @param {string} bookmark - للتنقل بين الصفحات
 */
async function scrapePinterest(query, bookmark = '') {
  const ua = pickRandom(USER_AGENTS);

  const options = {
    query,
    scope: 'pins',
    page_size: 50,
    ...(bookmark ? { bookmarks: [bookmark] } : {})
  };

  const response = await axios.get('https://www.pinterest.com/resource/BaseSearchResource/get/', {
    params: {
      source_url: `/search/pins/?q=${encodeURIComponent(query)}&rs=typed`,
      data: JSON.stringify({ options, context: {} }),
      _: Date.now()
    },
    headers: {
      'User-Agent': ua,
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'Accept-Language': 'en-US,en;q=0.9',
      'Accept-Encoding': 'gzip, deflate, br',
      'X-Requested-With': 'XMLHttpRequest',
      'X-Pinterest-AppState': 'active',
      'X-App-Version': '1.0.0',
      'Referer': `https://www.pinterest.com/search/pins/?q=${encodeURIComponent(query)}`,
      'Origin': 'https://www.pinterest.com',
      'DNT': '1',
      'Sec-Fetch-Dest': 'empty',
      'Sec-Fetch-Mode': 'cors',
      'Sec-Fetch-Site': 'same-origin'
    },
    timeout: 12000
  });

  const pins = extractPins(response.data);

  // فلترة صارمة: رفض أي صورة عرضها / ارتفاعها < 1.8
  const widePins = pins.filter(p => isWideBanner(p.width, p.height));

  return {
    pins: widePins,
    allPins: pins,
    bookmark: response.data?.resource_response?.bookmark || null
  };
}

function formatPin(pin, displayTerm, source) {
  const ratio = pin.height > 0 ? (pin.width / pin.height).toFixed(2) : '?';
  return {
    id: String(pin.id),
    title: pin.title?.trim().substring(0, 250) || 'Pinterest Banner',
    url: pin.url,
    pageUrl: pin.pageUrl,
    dimensions: `${Math.round(pin.width)}x${Math.round(pin.height)}`,
    ratio,
    source,
    displayTerm
  };
}

// ─── مكتبة كلمات البحث المتخصصة ──────────────────────────────────────────────

const BANNER_QUERIES = {
  anime: [
    'anime discord banner header wide',
    'anime banner aesthetic discord header',
    'anime scenery discord server banner'
  ],
  lofi: [
    'lofi discord banner header wide',
    'lofi aesthetic banner discord'
  ],
  cyberpunk: [
    'cyberpunk discord banner header wide',
    'neon cyberpunk banner aesthetic'
  ],
  gaming: [
    'gaming discord banner header wide',
    'esports gaming banner header'
  ],
  default: [
    '{q} discord banner header wide',
    '{q} banner header aesthetic wide',
    '{q} discord server banner'
  ]
};

function getBannerQueries(query) {
  const lower = query.toLowerCase();
  if (['anime','manga','naruto','genshin','demon','one piece','jujutsu','bleach'].some(k => lower.includes(k)))
    return BANNER_QUERIES.anime;
  if (lower.includes('lofi') || lower.includes('lo-fi'))
    return BANNER_QUERIES.lofi;
  if (lower.includes('cyberpunk') || lower.includes('neon'))
    return BANNER_QUERIES.cyberpunk;
  if (['gaming','game','esport','fps','minecraft'].some(k => lower.includes(k)))
    return BANNER_QUERIES.gaming;
  return BANNER_QUERIES.default.map(t => t.replace('{q}', query));
}

// ─────────────────────────────────────────────────────────────────────────────

const SURPRISE_QUERIES = [
  'anime discord banner header',
  'aesthetic discord banner header wide',
  'lofi discord banner header',
  'cyberpunk discord banner header',
  'dark aesthetic discord server banner'
];

export async function getSurpriseBanner() {
  const q = pickRandom(SURPRISE_QUERIES);
  return getSmartBanner(q, true);
}

export async function getSmartBanner(query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'anime';
  const source = isSurprise ? 'surprise' : 'search';
  const queries = getBannerQueries(rawTerm);

  // جرب كل قالب بحث حتى تجد بانر عريض
  for (const q of queries) {
    try {
      const { pins } = await scrapePinterest(q);
      if (pins.length > 0) {
        return formatPin(pickRandom(pins), rawTerm, source);
      }
    } catch (err) {
      console.warn(`[Pinterest] "${q}" failed:`, err.message);
    }
  }

  // محاولة أخيرة: بحث مباشر بـ discord banner header
  try {
    const { pins } = await scrapePinterest('discord banner header wide aesthetic');
    if (pins.length > 0) {
      return formatPin(pickRandom(pins), rawTerm, 'fallback');
    }
  } catch (e) {
    console.warn('[Pinterest fallback]', e.message);
  }

  // بانر طوارئ (رابط مباشر من Pinimg)
  return {
    id: 'emergency',
    title: 'Aesthetic Discord Banner',
    url: 'https://i.pinimg.com/originals/3e/5e/5e/3e5e5e0b0d7a2e4b2d2f1e6a1a9f1b2c.jpg',
    pageUrl: 'https://www.pinterest.com',
    dimensions: '1920x500',
    ratio: '3.84',
    source: 'emergency_fallback',
    displayTerm: rawTerm
  };
}
