import axios from 'axios';

const GIPHY_BASE_URL = 'https://api.giphy.com/v1/gifs';

/**
 * فلترة رياضية صارمة جداً للبانرات العريضة فقط
 * ترفض أي صورة إذا كان عرضها أقل من 1.75 ضعف ارتفاعها
 * (تمنع الصور المربعة والشبه مربعة والصور العمودية نهائياً)
 */
const MIN_BANNER_RATIO = 1.75;

/**
 * قوالب بحث متخصصة في جلب البانرات المتحركة لبروفايلات وسيرفرات ديسكورد
 */
const BANNER_QUERY_TEMPLATES = [
  query => `${query} discord banner gif`,
  query => `${query} banner gif`,
  query => `${query} header landscape gif`,
  query => `${query} wide header gif`
];

/**
 * مكتبة بانرات ديسكورد عريضة وجمالية جاهزة في حال كان البحث نادراً جداً
 */
const CURATED_DISCORD_BANNERS = [
  'anime discord banner gif',
  'lofi anime banner gif',
  'cyberpunk banner landscape',
  'pixel art banner gif',
  'aesthetic discord header gif',
  'retrowave synthwave banner gif',
  'galaxy space banner landscape',
  'japan aesthetic banner gif'
];

/**
 * اختيار عشوائي من مصفوفة
 * @param {Array} array 
 * @returns {*}
 */
function pickRandom(array) {
  if (!Array.isArray(array) || array.length === 0) return null;
  return array[Math.floor(Math.random() * array.length)];
}

/**
 * فحص نسبة الأبعاد لضمان أنها بانر أفقي عريض حقيقي
 * @param {Object} item 
 * @returns {boolean}
 */
export function isRealWideBanner(item) {
  const original = item?.images?.original;
  if (!original) return false;

  const width = parseFloat(original.width);
  const height = parseFloat(original.height);

  if (!width || !height || isNaN(width) || isNaN(height) || height <= 0) {
    return false;
  }

  // العرض يجب أن يكون على الأقل 1.75 ضعف الارتفاع
  const ratio = width / height;
  return ratio >= MIN_BANNER_RATIO;
}

/**
 * تنسيق بيانات البانر لرسالة Embed
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
                    item.url;

  const width = Math.round(parseFloat(item.images?.original?.width || 0));
  const height = Math.round(parseFloat(item.images?.original?.height || 0));
  const ratio = (width / height).toFixed(2);

  return {
    id: item.id || 'unknown',
    title: item.title && item.title.trim().length > 0 ? item.title.trim() : 'Discord Animated Banner',
    url: bannerUrl,
    giphyUrl: item.url || 'https://giphy.com',
    dimensions: width && height ? `${width}x${height}` : 'Wide Banner',
    ratio: isNaN(ratio) ? 'Wide' : ratio,
    source,
    displayTerm
  };
}

/**
 * جلب بانر مفاجئ عشوائي
 * @param {string} apiKey 
 * @returns {Promise<Object>}
 */
export async function getSurpriseBanner(apiKey) {
  const randomTheme = pickRandom(CURATED_DISCORD_BANNERS);
  return getSmartBanner(apiKey, randomTheme, true);
}

/**
 * المحرك الرئيسي للبحث عن البانرات العريضة فقط
 * @param {string} apiKey 
 * @param {string} query 
 * @param {boolean} isSurprise 
 * @returns {Promise<Object>}
 */
export async function getSmartBanner(apiKey, query, isSurprise = false) {
  const rawTerm = query ? query.trim() : 'anime';

  if (apiKey && apiKey.trim().length > 0) {
    // نجرب صياغات البحث المتخصصة في البانرات
    for (const template of BANNER_QUERY_TEMPLATES) {
      const q = template(rawTerm);
      try {
        const offset = Math.floor(Math.random() * 15);
        const response = await axios.get(`${GIPHY_BASE_URL}/search`, {
          params: {
            api_key: apiKey,
            q,
            limit: 50, // جلب 50 نتيجة لفحص واختيار البانرات الأفقية الحقيقية
            offset,
            rating: 'pg-13',
            lang: 'en'
          },
          timeout: 7000
        });

        const results = response.data?.data;
        if (Array.isArray(results) && results.length > 0) {
          // فلترة صارمة: فقط البانرات التي عرضها >= 1.75 من ارتفاعها
          const wideBanners = results.filter(isRealWideBanner);
          if (wideBanners.length > 0) {
            const selected = pickRandom(wideBanners);
            return formatBannerResponse(selected, isSurprise ? 'surprise' : 'search', rawTerm);
          }
        }
      } catch (err) {
        console.warn(`Query for banner failed:`, err.message);
      }
    }

    // إذا لم يعثر على بانر يطابق الكلمة بالنسبة الصارمة، يجلب بانر جمالي بديل من المكتبة
    try {
      const fallbackQuery = pickRandom(CURATED_DISCORD_BANNERS);
      const fallbackRes = await axios.get(`${GIPHY_BASE_URL}/search`, {
        params: {
          api_key: apiKey,
          q: fallbackQuery,
          limit: 50,
          offset: Math.floor(Math.random() * 10),
          rating: 'pg-13'
        },
        timeout: 7000
      });

      const fallbackResults = fallbackRes.data?.data;
      if (Array.isArray(fallbackResults) && fallbackResults.length > 0) {
        const validWide = fallbackResults.filter(isRealWideBanner);
        if (validWide.length > 0) {
          const selected = pickRandom(validWide);
          return formatBannerResponse(selected, 'fallback', fallbackQuery.replace(' discord banner gif', ''));
        }
      }
    } catch (e) {
      console.warn('Fallback banner search error:', e.message);
    }
  }

  // بانر طوارئ ألترا وايد عالي الدقة (نسبة 2.5)
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
