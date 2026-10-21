import axios from 'axios';

const GIPHY_BASE_URL = 'https://api.giphy.com/v1/gifs';

/**
 * Fallback keywords to query if everything else fails
 */
const FALLBACK_KEYWORDS = ['reaction', 'funny', 'excited', 'party', 'vibes', 'dance', 'yay'];

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
 * Normalizes a Giphy item into a standardized payload
 * @param {Object} item - Giphy API GIF object
 * @param {string} source - How the GIF was retrieved ('search', 'trending', 'random', 'fallback')
 * @param {string} displayTerm - Search term or description to display
 * @returns {Object|null}
 */
function formatGifResponse(item, source, displayTerm) {
  if (!item) return null;

  // Prefer original GIF URL, fallback to downsized or standard web URL
  const gifUrl = item.images?.original?.url ||
                 item.images?.downsized_medium?.url ||
                 item.images?.downsized?.url ||
                 item.url;

  return {
    id: item.id || 'unknown',
    title: item.title && item.title.trim().length > 0 ? item.title.trim() : 'GIF',
    url: gifUrl,
    giphyUrl: item.url || 'https://giphy.com',
    source,
    displayTerm
  };
}

/**
 * Fetches trending GIFs from Giphy
 * @param {string} apiKey 
 * @param {number} limit 
 * @returns {Promise<Object|null>}
 */
export async function getTrendingGif(apiKey, limit = 25) {
  try {
    const offset = Math.floor(Math.random() * 50); // Randomize trending offset
    const response = await axios.get(`${GIPHY_BASE_URL}/trending`, {
      params: {
        api_key: apiKey,
        limit,
        offset,
        rating: 'pg-13'
      },
      timeout: 7000
    });

    const data = response.data?.data;
    if (Array.isArray(data) && data.length > 0) {
      const selected = pickRandom(data);
      return formatGifResponse(selected, 'trending', 'Trending');
    }
  } catch (error) {
    console.error('Failed to fetch trending GIF:', error.response?.data?.message || error.message);
  }
  return null;
}

/**
 * Fetches a random GIF from Giphy by tag
 * @param {string} apiKey 
 * @param {string} tag 
 * @returns {Promise<Object|null>}
 */
export async function getRandomGif(apiKey, tag = '') {
  try {
    const response = await axios.get(`${GIPHY_BASE_URL}/random`, {
      params: {
        api_key: apiKey,
        tag: tag || undefined,
        rating: 'pg-13'
      },
      timeout: 7000
    });

    const data = response.data?.data;
    if (data && (data.images?.original?.url || data.url)) {
      return formatGifResponse(data, 'random', tag || 'Surprise');
    }
  } catch (error) {
    console.error('Failed to fetch random GIF:', error.response?.data?.message || error.message);
  }
  return null;
}

/**
 * Primary Smart Search with Multi-Tier Fallback Mechanism
 * Tier 1: Search user's exact query (randomized offset within top results)
 * Tier 2: Strip symbols & search simplified query or individual keywords
 * Tier 3: Random GIF using search tag
 * Tier 4: Search one of the curated fallback reaction keywords
 * Tier 5: Trending GIF
 * Tier 6: Hardcoded ultra-reliable emergency reaction GIF
 *
 * @param {string} apiKey - Giphy API Key
 * @param {string} query - User search term
 * @returns {Promise<Object>} Formatted GIF object guaranteed not to fail
 */
export async function getSmartGif(apiKey, query) {
  const cleanQuery = query ? query.trim() : '';

  // 1. Direct Search with Randomized Offset
  if (cleanQuery.length > 0) {
    try {
      const searchOffset = Math.floor(Math.random() * 25);
      const response = await axios.get(`${GIPHY_BASE_URL}/search`, {
        params: {
          api_key: apiKey,
          q: cleanQuery,
          limit: 25,
          offset: searchOffset,
          rating: 'pg-13',
          lang: 'en'
        },
        timeout: 7000
      });

      const results = response.data?.data;
      if (Array.isArray(results) && results.length > 0) {
        const selected = pickRandom(results);
        return formatGifResponse(selected, 'search', cleanQuery);
      }

      // If offset was too high and returned 0, retry with offset 0
      if (searchOffset > 0) {
        const retryResponse = await axios.get(`${GIPHY_BASE_URL}/search`, {
          params: {
            api_key: apiKey,
            q: cleanQuery,
            limit: 25,
            offset: 0,
            rating: 'pg-13',
            lang: 'en'
          },
          timeout: 7000
        });

        const retryResults = retryResponse.data?.data;
        if (Array.isArray(retryResults) && retryResults.length > 0) {
          const selected = pickRandom(retryResults);
          return formatGifResponse(selected, 'search', cleanQuery);
        }
      }
    } catch (error) {
      console.warn(`Search error for "${cleanQuery}":`, error.response?.data?.message || error.message);
    }

    // 2. Fallback: Try Giphy Random endpoint with query as tag
    const randomTagged = await getRandomGif(apiKey, cleanQuery);
    if (randomTagged) return randomTagged;
  }

  // 3. Fallback: Try a curated fallback reaction query
  const fallbackTag = pickRandom(FALLBACK_KEYWORDS);
  try {
    const fallbackResponse = await axios.get(`${GIPHY_BASE_URL}/search`, {
      params: {
        api_key: apiKey,
        q: fallbackTag,
        limit: 20,
        offset: Math.floor(Math.random() * 20),
        rating: 'pg-13'
      },
      timeout: 7000
    });

    const fallbackResults = fallbackResponse.data?.data;
    if (Array.isArray(fallbackResults) && fallbackResults.length > 0) {
      const selected = pickRandom(fallbackResults);
      return formatGifResponse(selected, 'fallback', fallbackTag);
    }
  } catch (error) {
    console.warn(`Fallback search error for "${fallbackTag}":`, error.message);
  }

  // 4. Fallback: Fetch Trending GIF
  const trending = await getTrendingGif(apiKey);
  if (trending) return trending;

  // 5. Ultimate Fallback: High-availability static Giphy CDN link
  return {
    id: 'emergency-fallback',
    title: 'Party Celebration',
    url: 'https://media.giphy.com/media/26AHONQ79FdWZhAI0/giphy.gif',
    giphyUrl: 'https://giphy.com',
    source: 'emergency_fallback',
    displayTerm: cleanQuery || 'Surprise'
  };
}
