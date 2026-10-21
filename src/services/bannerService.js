import axios from 'axios';

const GIPHY_BASE_URL = 'https://api.giphy.com/v1/gifs';

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
 * Validates whether an image is wide/landscape (aspect ratio >= 1.25)
 * @param {Object} item 
 * @returns {boolean}
 */
function isWideAspectRatio(item) {
  const original = item?.images?.original;
  if (!original) return true; // fallback to true if dimensions missing

  const width = parseInt(original.width, 10);
  const height = parseInt(original.height, 10);

  if (isNaN(width) || isNaN(height) || height === 0) return true;
  return (width / height) >= 1.25;
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
 * Smart Banner Search Engine with Banner-Optimization & Aspect-Ratio Filtering
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

  // 1. Optimized Banner Search
  try {
    const searchOffset = Math.floor(Math.random() * 20);
    const response = await axios.get(`${GIPHY_BASE_URL}/search`, {
      params: {
        api_key: apiKey,
        q: optimizedQuery,
        limit: 30,
        offset: searchOffset,
        rating: 'pg-13',
        lang: 'en'
      },
      timeout: 7000
    });

    const results = response.data?.data;
    if (Array.isArray(results) && results.length > 0) {
      // Filter for wide/landscape banners first
      const wideBanners = results.filter(isWideAspectRatio);
      const candidates = wideBanners.length > 0 ? wideBanners : results;
      const selected = pickRandom(candidates);
      return formatBannerResponse(selected, isSurprise ? 'surprise' : 'optimized', rawTerm);
    }
  } catch (error) {
    console.warn(`Banner search error for "${optimizedQuery}":`, error.response?.data?.message || error.message);
  }

  // 2. Retry with raw term + fallback offset 0
  try {
    const retryResponse = await axios.get(`${GIPHY_BASE_URL}/search`, {
      params: {
        api_key: apiKey,
        q: `${rawTerm} banner`,
        limit: 25,
        offset: 0,
        rating: 'pg-13'
      },
      timeout: 7000
    });

    const retryResults = retryResponse.data?.data;
    if (Array.isArray(retryResults) && retryResults.length > 0) {
      const selected = pickRandom(retryResults);
      return formatBannerResponse(selected, 'search', rawTerm);
    }
  } catch (err) {
    console.warn(`Retry banner search error:`, err.message);
  }

  // 3. Fallback to Curated Aesthetic Banners
  try {
    const fallbackTheme = pickRandom(FALLBACK_BANNER_THEMES);
    const fallbackResponse = await axios.get(`${GIPHY_BASE_URL}/search`, {
      params: {
        api_key: apiKey,
        q: fallbackTheme,
        limit: 25,
        offset: Math.floor(Math.random() * 15),
        rating: 'pg-13'
      },
      timeout: 7000
    });

    const fallbackResults = fallbackResponse.data?.data;
    if (Array.isArray(fallbackResults) && fallbackResults.length > 0) {
      const wideFallback = fallbackResults.filter(isWideAspectRatio);
      const selected = pickRandom(wideFallback.length > 0 ? wideFallback : fallbackResults);
      return formatBannerResponse(selected, 'fallback', fallbackTheme);
    }
  } catch (err) {
    console.warn(`Fallback banner theme search failed:`, err.message);
  }

  // 4. Reliable Emergency High-Definition Landscape Banner
  return {
    id: 'emergency-banner',
    title: 'Aesthetic Cyber Cityscape Banner',
    url: 'https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif',
    giphyUrl: 'https://giphy.com',
    dimensions: '1000x400',
    source: 'emergency_fallback',
    displayTerm: rawTerm
  };
}
