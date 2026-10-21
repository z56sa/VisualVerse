import axios from 'axios';

const GIPHY_BASE_URL = 'https://api.giphy.com/v1/gifs';

/**
 * Strict Aspect Ratio Threshold for Banners:
 * Standard Discord profile/server banners are 16:9 (1.77) or wider (~2.5 to 3.0).
 * Threshold >= 1.7 completely filters out regular square/portrait GIFs.
 */
const MIN_BANNER_ASPECT_RATIO = 1.7;

/**
 * High-intent banner search terms to force Giphy to return true horizontal landscape banners
 */
const BANNER_SPECIALIZED_KEYWORDS = [
  'banner aesthetic',
  'discord banner',
  'profile banner',
  'header landscape',
  'wide banner',
  'anime banner gif',
  'landscape header'
];

/**
 * Curated ultra-wide aesthetic banner themes
 */
const CURATED_BANNER_COLLECTIONS = [
  'lofi anime banner',
  'cyberpunk city banner',
  'aesthetic landscape banner',
  'pixel art banner',
  'retrowave synthwave banner',
  'galaxy space banner',
  'nature sunset banner',
  'japanese aesthetic banner',
  'chill vibes banner',
  'dark aesthetic header'
];

/**
 * Helper to pick a random item from an array
 * @param {Array} array 
 * @returns {*}
 */
function pickRandom(array) {
  if (!Array.isArray(array) || array.length === 0) return null;
  return array[Math.floor(Math.random() * array.length)];
}

/**
 * فلترة رياضية صارمة جداً: ترفض أي GIF عادي، مربع، أو عمودي،
 * وتقبل فقط البانرات الحقيقية العريضة جداً (عرض / ارتفاع >= 1.7)
 * @param {Object} item 
 * @returns {boolean}
 */
export function isStrictBanner(item) {
  const width = parseFloat(item.media_formats?.gif?.dims?.[0] || item.images?.original?.width || 0);
  const height = parseFloat(item.media_formats?.gif?.dims?.[1] || item.images?.original?.height || 1);

  if (!width || !height || isNaN(width) || isNaN(height) || height <= 0) {
    return false;
  }

  const aspectRatio = width / height;
  return aspectRatio >= MIN_BANNER_ASPECT_RATIO;
}

/**
 * تطبيق الفلترة الصارمة على النتائج
 * @param {Array} items 
 * @returns {Array}
 */
export function filterStrictBanners(items) {
  if (!Array.isArray(items)) return [];
  return items.filter(isStrictBanner);
}

/**
 * توحيد هيكل بيانات البانر لـ Discord Embed
 * @param {Object} item 
 * @param {string} source 
 * @param {string} displayTerm 
 * @returns {Object}
 */
function formatBannerResponse(item, source, displayTerm) {
  if (!item) return null;

  const bannerUrl = item.images?.original?.url ||
                    item.images?.downsized_large?.url ||
                    item.images?.downsized_medium?.url ||
                    item.media_formats?.gif?.url ||
                    item.url;

  const width = parseFloat(item.media_formats?.gif?.dims?.[0] || item.images?.original?.width || 0);
  const height = parseFloat(item.media_formats?.gif?.dims?.[1] || item.images?.original?.height || 1);
  const ratio = (width / height).toFixed(2);

  return {
    id: item.id || 'unknown',
    title: item.title && item.title.trim().length > 0 ? item.title.trim() : 'Discord Animated Banner',
    url: bannerUrl,
    giphyUrl: item.url || 'https://giphy.com',
    dimensions: `${Math.round(width)}x${Math.round(height)}`,
    ratio: isNaN(ratio) ? 'Wide' : ratio,
    source,
    displayTerm
  };
}

/**
 * جلب بانر عريض عشوائي ومفاجئ
 * @param {string} apiKey 
 * @returns {Promise<Object>}
 */
export async function getSurpriseBanner(apiKey) {
  const randomTheme = pickRandom(CURATED_BANNER_COLLECTIONS);
  return getSmartBanner(apiKey, randomTheme, true);
}

/**
 * محرك البحث المتخصص حصراً في البانرات العريضة (Banners Only Engine)
 * @param {string} apiKey 
 * @param {string} query - مصطلح البحث
 * @param {boolean} isSurprise 
 * @returns {Promise<Object>}
 */
export async function getSmartBanner(apiKey, query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'aesthetic';

  // 1. صياغة كلمات بحث تركز كلياً على البانر وHeader الديسكورد
  const lowerQuery = rawTerm.toLowerCase();
  let searchQueries = [];

  if (lowerQuery.includes('banner') || lowerQuery.includes('header')) {
    searchQueries = [rawTerm, `${rawTerm} discord`, `${rawTerm} landscape`];
  } else {
    searchQueries = [
      `${rawTerm} discord banner`,
      `${rawTerm} banner`,
      `${rawTerm} header landscape`,
      `${rawTerm} wide header`
    ];
  }

  if (apiKey && apiKey.trim().length > 0) {
    // المحاولة بالصيغ المخصصة للبانرات
    for (const searchQuery of searchQueries) {
      try {
        const offset = Math.floor(Math.random() * 15);
        const response = await axios.get(`${GIPHY_BASE_URL}/search`, {
          params: {
            api_key: apiKey,
            q: searchQuery,
            limit: 50, // جلب حزمة كبيرة من 50 نتيجة
            offset,
            rating: 'pg-13',
            lang: 'en'
          },
          timeout: 7000
        });

        const results = response.data?.data;
        if (Array.isArray(results) && results.length > 0) {
          // تطبيق شرط البانر الصارم (aspectRatio >= 1.7)
          const validBanners = filterStrictBanners(results);
          if (validBanners.length > 0) {
            const selected = pickRandom(validBanners);
            return formatBannerResponse(selected, isSurprise ? 'surprise' : 'custom_search', rawTerm);
          }
        }
      } catch (err) {
        console.warn(`Query "${searchQuery}" failed:`, err.message);
      }
    }

    // 2. إذا لم يعثر على بانر يطابق الكلمة الدقيقة مع نسبة 1.7، يجلب بانر من المجموعات العريضة الجمالية
    try {
      const fallbackCollection = pickRandom(CURATED_BANNER_COLLECTIONS);
      const fallbackResponse = await axios.get(`${GIPHY_BASE_URL}/search`, {
        params: {
          api_key: apiKey,
          q: fallbackCollection,
          limit: 50,
          offset: Math.floor(Math.random() * 10),
          rating: 'pg-13'
        },
        timeout: 7000
      });

      const fallbackResults = fallbackResponse.data?.data;
      if (Array.isArray(fallbackResults) && fallbackResults.length > 0) {
        const validFallbacks = filterStrictBanners(fallbackResults);
        if (validFallbacks.length > 0) {
          const selected = pickRandom(validFallbacks);
          return formatBannerResponse(selected, 'fallback', fallbackCollection);
        }
      }
    } catch (fallbackErr) {
      console.warn('Fallback banner collection query failed:', fallbackErr.message);
    }
  }

  // 3. بانر طوارئ ألترا وايد عالي الدقة (نسبة 2.5: 1000x400)
  return {
    id: 'emergency-banner',
    title: 'Aesthetic Cyber Cityscape Banner',
    url: 'https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif',
    giphyUrl: 'https://giphy.com',
    dimensions: '1000x400',
    ratio: '2.50',
    source: 'emergency_fallback',
    displayTerm: rawTerm
  };
}
