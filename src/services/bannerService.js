import axios from 'axios';

const GIPHY_BASE_URL = 'https://api.giphy.com/v1/gifs';

/**
 * Minimum aspect ratio required for a banner (width / height >= 1.6)
 * Typical banner formats: 16:9 (1.77), 2:1 (2.0), 3:1 (3.0), etc.
 */
const MIN_BANNER_ASPECT_RATIO = 1.6;

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
 * Strict Aspect Ratio Validator:
 * Checks width and height properties for each result.
 * Strictly requires (width / height >= 1.6).
 * Skips any square, tall, or near-square GIFs.
 * 
 * @param {Object} item - Giphy API GIF object
 * @returns {boolean} true only if wide/landscape
 */
export function isStrictBannerAspectRatio(item) {
  const original = item?.images?.original;
  if (!original) return false;

  const width = parseFloat(original.width);
  const height = parseFloat(original.height);

  if (!width || !height || isNaN(width) || isNaN(height) || height <= 0) {
    return false;
  }

  const ratio = width / height;
  return ratio >= MIN_BANNER_ASPECT_RATIO;
}

/**
 * Normalizes a Giphy item into a standardized Banner payload
 * @param {Object} item - Giphy API GIF object
 * @param {string} source - How it was retrieved ('search', 'optimized', 'surprise', 'fallback')
 * @param {string} displayTerm - Search term or description to display
 * @returns {Object|null}
 */
function formatBannerResponse(item, source, displayTerm) {
  if (!item) return null;

  const gifUrl = item.images?.original?.url ||
                 item.images?.downsized_large?.url ||
                 item.images?.downsized_medium?.url ||
                 item.url;

  const width = item.images?.original?.width || 'Auto';
  const height = item.images?.original?.height || 'Auto';

  return {
    id: item.id || 'unknown',
    title: item.title && item.title.trim().length > 0 ? item.title.trim() : 'Animated Banner',
    url: gifUrl,
    giphyUrl: item.url || 'https://giphy.com',
    dimensions: `${width}x${height}`,
    ratio: (parseFloat(width) / parseFloat(height)).toFixed(2),
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
 * Smart Banner Search Engine with STRICT Aspect-Ratio Filtering (>= 1.6)
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

  // 1. Optimized Banner Search with Strict Filter
  try {
    const searchOffset = Math.floor(Math.random() * 20);
    const response = await axios.get(`${GIPHY_BASE_URL}/search`, {
      params: {
        api_key: apiKey,
        q: optimizedQuery,
        limit: 50, // request larger batch to ensure plenty of wide candidates
        offset: searchOffset,
        rating: 'pg-13',
        lang: 'en'
      },
      timeout: 7000
    });

    const results = response.data?.data;
    if (Array.isArray(results) && results.length > 0) {
      // STRICT FILTER: width / height >= 1.6 (skip square/tall GIFs)
      const wideBanners = results.filter(isStrictBannerAspectRatio);
      if (wideBanners.length > 0) {
        const selected = pickRandom(wideBanners);
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
      const wideRetry = retryResults.filter(isStrictBannerAspectRatio);
      if (wideRetry.length > 0) {
        const selected = pickRandom(wideRetry);
        return formatBannerResponse(selected, 'search', rawTerm);
      }
    }
  } catch (err) {
    console.warn(`Retry banner search error:`, err.message);
  }

  // 3. Fallback to Curated Aesthetic Banners with strict filter
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
      const wideFallback = fallbackResults.filter(isStrictBannerAspectRatio);
      if (wideFallback.length > 0) {
        const selected = pickRandom(wideFallback);
        return formatBannerResponse(selected, 'fallback', fallbackTheme);
      }
    }
  } catch (err) {
    console.warn(`Fallback banner theme search failed:`, err.message);
  }

  // 4. Reliable Emergency High-Definition Ultra-Wide Landscape Banner (Ratio: 2.5)
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
