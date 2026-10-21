import axios from 'axios';

const GIPHY_BASE_URL = 'https://api.giphy.com/v1/gifs';

/**
 * Strict Aspect Ratio Threshold:
 * Requires (width / height >= 1.7) to ensure only genuine, ultra-wide landscape banners are returned.
 */
const MIN_BANNER_ASPECT_RATIO = 1.7;

/**
 * Banner optimization suffixes to append to search queries
 */
const BANNER_SUFFIXES = ['banner', 'header', 'landscape', 'wide animated', 'aesthetic header'];

/**
 * Fallback banner themes when user query returns no wide matches
 */
const FALLBACK_BANNER_THEMES = [
  'aesthetic landscape banner',
  'anime banner',
  'cyberpunk header',
  'pixel art banner',
  'retro wave header',
  'space galaxy banner',
  'lofi landscape'
];

/**
 * Picks a random item from an array
 * @param {Array} array 
 * @returns {*}
 */
function pickRandom(array) {
  if (!Array.isArray(array) || array.length === 0) return null;
  return array[Math.floor(Math.random() * array.length)];
}

/**
 * فلترة صارمة جداً تمنع أي صورة مربعة أو عمودية أو قريبة من المربع
 * يدعم كلا من Giphy (images.original) و Tenor (media_formats.gif.dims)
 * @param {Object} item 
 * @returns {boolean}
 */
export function isStrictBanner(item) {
  const width = parseFloat(item.media_formats?.gif?.dims?.[0] || item.images?.original?.width || 0);
  const height = parseFloat(item.media_formats?.gif?.dims?.[1] || item.images?.original?.height || 1);

  if (!width || !height || isNaN(width) || isNaN(height) || height <= 0) {
    return false;
  }

  // شرط أن يكون العرض أضعاف الارتفاع (نسبة 1.7 أو أكثر ليكون بانر عريض فعلياً)
  const aspectRatio = width / height;
  return aspectRatio >= MIN_BANNER_ASPECT_RATIO;
}

/**
 * تطبيق الفلترة الصارمة على قائمة نتائج
 * @param {Array} items 
 * @returns {Array}
 */
export function filterStrictBannerResults(items) {
  if (!Array.isArray(items)) return [];
  return items.filter(isStrictBanner);
}

/**
 * Normalizes an API item into a standardized Banner payload
 * @param {Object} item - GIF object
 * @param {string} source - How it was retrieved ('search', 'optimized', 'surprise', 'fallback')
 * @param {string} displayTerm - Search term or description to display
 * @returns {Object|null}
 */
function formatBannerResponse(item, source, displayTerm) {
  if (!item) return null;

  const gifUrl = item.images?.original?.url ||
                 item.images?.downsized_large?.url ||
                 item.images?.downsized_medium?.url ||
                 item.media_formats?.gif?.url ||
                 item.url;

  const width = item.media_formats?.gif?.dims?.[0] || item.images?.original?.width || 'Auto';
  const height = item.media_formats?.gif?.dims?.[1] || item.images?.original?.height || 'Auto';

  const numericRatio = (parseFloat(width) / parseFloat(height)).toFixed(2);

  return {
    id: item.id || 'unknown',
    title: item.title && item.title.trim().length > 0 ? item.title.trim() : 'Animated Banner',
    url: gifUrl,
    giphyUrl: item.url || 'https://giphy.com',
    dimensions: `${width}x${height}`,
    ratio: isNaN(numericRatio) ? 'Wide' : numericRatio,
    source,
    displayTerm
  };
}

/**
 * Fetches a surprise/random wide animated banner
 * @param {string} apiKey 
 * @returns {Promise<Object>}
 */
export async function getSurpriseBanner(apiKey) {
  const randomTheme = pickRandom(FALLBACK_BANNER_THEMES);
  return getSmartBanner(apiKey, randomTheme, true);
}

/**
 * Smart Banner Search Engine with STRICT Aspect-Ratio Filtering (>= 1.7)
 * @param {string} apiKey 
 * @param {string} query 
 * @param {boolean} isSurprise 
 * @returns {Promise<Object>}
 */
export async function getSmartBanner(apiKey, query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'aesthetic';
  const suffix = pickRandom(BANNER_SUFFIXES);

  // If user already included 'banner' or 'header', don't duplicate
  const lowerQuery = rawTerm.toLowerCase();
  const optimizedQuery = (lowerQuery.includes('banner') || lowerQuery.includes('header') || lowerQuery.includes('landscape'))
    ? rawTerm
    : `${rawTerm} ${suffix}`;

  // 1. Optimized Banner Search with Strict Filter (aspectRatio >= 1.7)
  if (apiKey && apiKey.trim().length > 0) {
    try {
      const searchOffset = Math.floor(Math.random() * 20);
      const response = await axios.get(`${GIPHY_BASE_URL}/search`, {
        params: {
          api_key: apiKey,
          q: optimizedQuery,
          limit: 50, // جلب 50 نتيجة لاختيار أفضل البانرات العريضة منها
          offset: searchOffset,
          rating: 'pg-13',
          lang: 'en'
        },
        timeout: 7000
      });

      const results = response.data?.data;
      if (Array.isArray(results) && results.length > 0) {
        // فلترة صارمة جداً تمنع أي صورة مربعة أو عمودية
        const filteredResults = filterStrictBannerResults(results);
        if (filteredResults.length > 0) {
          const selected = pickRandom(filteredResults);
          return formatBannerResponse(selected, isSurprise ? 'surprise' : 'optimized', rawTerm);
        }
      }
    } catch (error) {
      console.warn(`Banner search error for "${optimizedQuery}":`, error.response?.data?.message || error.message);
    }

    // 2. Retry with raw term + 'banner' with offset 0 and strict filter
    try {
      const retryResponse = await axios.get(`${GIPHY_BASE_URL}/search`, {
        params: {
          api_key: apiKey,
          q: `${rawTerm} banner`,
          limit: 50,
          offset: 0,
          rating: 'pg-13'
        },
        timeout: 7000
      });

      const retryResults = retryResponse.data?.data;
      if (Array.isArray(retryResults) && retryResults.length > 0) {
        const filteredRetry = filterStrictBannerResults(retryResults);
        if (filteredRetry.length > 0) {
          const selected = pickRandom(filteredRetry);
          return formatBannerResponse(selected, 'search', rawTerm);
        }
      }
    } catch (err) {
      console.warn(`Retry banner search error:`, err.message);
    }

    // 3. Fallback to Curated Aesthetic Banners with strict filter (aspectRatio >= 1.7)
    try {
      const fallbackTheme = pickRandom(FALLBACK_BANNER_THEMES);
      const fallbackResponse = await axios.get(`${GIPHY_BASE_URL}/search`, {
        params: {
          api_key: apiKey,
          q: fallbackTheme,
          limit: 40,
          offset: Math.floor(Math.random() * 15),
          rating: 'pg-13'
        },
        timeout: 7000
      });

      const fallbackResults = fallbackResponse.data?.data;
      if (Array.isArray(fallbackResults) && fallbackResults.length > 0) {
        const filteredFallback = filterStrictBannerResults(fallbackResults);
        if (filteredFallback.length > 0) {
          const selected = pickRandom(filteredFallback);
          return formatBannerResponse(selected, 'fallback', fallbackTheme);
        }
      }
    } catch (err) {
      console.warn(`Fallback banner theme search failed:`, err.message);
    }
  }

  // 4. Reliable Emergency High-Definition Ultra-Wide Landscape Banner (Aspect Ratio: 2.5)
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
