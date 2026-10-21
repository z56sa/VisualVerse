import Parser from 'rss-parser';

const parser = new Parser({
  customFields: {
    item: [
      ['media:content', 'mediaContent'],
      ['media:thumbnail', 'mediaThumbnail'],
      ['enclosure', 'enclosure']
    ]
  },
  headers: {
    'User-Agent': 'FeedPulseBot/1.0 (Discord RSS Aggregator)'
  },
  timeout: 10000
});

/**
 * مصادر أخبار افتراضية جاهزة (ألعاب، تقنية، أنمي)
 */
export const DEFAULT_FEEDS = [
  { name: 'IGN Gaming', url: 'https://feeds.feedburner.com/ign/all', category: 'gaming' },
  { name: 'The Verge Tech', url: 'https://www.theverge.com/rss/index.xml', category: 'tech' },
  { name: 'Anime News Network', url: 'https://www.animenewsnetwork.com/news/rss.xml', category: 'anime' }
];

/**
 * استخراج صورة الخبر بدقة من محتوى الـ RSS
 * @param {Object} item 
 * @returns {string|null}
 */
export function extractImageUrl(item) {
  // 1. media:content
  if (item.mediaContent?.$?.url) return item.mediaContent.$.url;

  // 2. media:thumbnail
  if (item.mediaThumbnail?.$?.url) return item.mediaThumbnail.$.url;

  // 3. enclosure (إذا كان صورة)
  if (item.enclosure?.url && (item.enclosure.type?.startsWith('image') || item.enclosure.url.match(/\.(jpeg|jpg|png|webp|gif)/i))) {
    return item.enclosure.url;
  }

  // 4. استخراج وسم <img> من محتوى HTML
  const htmlContent = item['content:encoded'] || item.content || item.description || '';
  const imgMatch = htmlContent.match(/<img[^>]+src=["']([^"']+)["']/i);
  if (imgMatch && imgMatch[1]) {
    return imgMatch[1];
  }

  return null;
}

/**
 * جلب أحدث الأخبار من رابط RSS محدد
 * @param {string} rssUrl 
 * @param {number} limit 
 * @returns {Promise<{ feedTitle: string, items: Array }>}
 */
export async function fetchFeedItems(rssUrl, limit = 5) {
  try {
    const feed = await parser.parseURL(rssUrl);
    const items = (feed.items || []).slice(0, limit).map(item => ({
      title: item.title ? item.title.trim() : 'خبر بدون عنوان',
      link: item.link || '',
      pubDate: item.pubDate ? new Date(item.pubDate) : new Date(),
      contentSnippet: item.contentSnippet || item.content || '',
      imageUrl: extractImageUrl(item),
      feedTitle: feed.title || 'مصدر إخباري'
    }));

    return {
      feedTitle: feed.title || 'مصدر إخباري',
      items
    };
  } catch (error) {
    console.error(`❌ خطأ في جلب خلاصة RSS من ${rssUrl}:`, error.message);
    throw error;
  }
}
