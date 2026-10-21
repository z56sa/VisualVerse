import { fetchFeedItems } from './feedService.js';
import { summarizeNewsItem } from './aiService.js';
import { loadFeedsConfig, saveFeedsConfig } from './storageService.js';
import { createNewsEmbed, createNewsActionRow } from '../utils/embedBuilder.js';

let isChecking = false;

/**
 * فحص الخلاصات المسجلة لكل السيرفرات وإرسال الأخبار الجديدة فوراً
 * @param {import('discord.js').Client} client 
 * @param {string} geminiApiKey 
 */
export async function checkFeedsAndBroadcast(client, geminiApiKey) {
  if (isChecking) return;
  isChecking = true;

  try {
    const config = loadFeedsConfig();
    const guildIds = Object.keys(config);

    for (const guildId of guildIds) {
      const guildData = config[guildId];
      if (!guildData.channelId || !Array.isArray(guildData.feeds) || guildData.feeds.length === 0) {
        continue;
      }

      const channel = await client.channels.fetch(guildData.channelId).catch(() => null);
      if (!channel || !channel.isTextBased()) continue;

      if (!Array.isArray(guildData.lastPostedUrls)) {
        guildData.lastPostedUrls = [];
      }

      for (const feedUrl of guildData.feeds) {
        try {
          const feed = await fetchFeedItems(feedUrl, 3);
          const newItems = feed.items.filter(item => !guildData.lastPostedUrls.includes(item.link));

          // نرسل الأخبار من الأقدم للأحدث إذا كان هناك أكثر من خبر جديد
          for (const item of newItems.reverse()) {
            console.log(`📢 [FeedPulse] خبر جديد تم اكتشافه: ${item.title}`);

            const aiResult = await summarizeNewsItem(geminiApiKey, item.title, item.contentSnippet);
            const embed = createNewsEmbed({
              arabicTitle: aiResult.arabicTitle,
              originalTitle: item.title,
              summaryPoints: aiResult.summaryPoints,
              link: item.link,
              imageUrl: item.imageUrl,
              pubDate: item.pubDate,
              sourceName: feed.feedTitle
            });
            const row = createNewsActionRow(item.link);

            await channel.send({ embeds: [embed], components: [row] });

            guildData.lastPostedUrls.push(item.link);
            if (guildData.lastPostedUrls.length > 100) {
              guildData.lastPostedUrls = guildData.lastPostedUrls.slice(-100);
            }
          }
        } catch (feedErr) {
          console.warn(`[AutoFeed] Feed error for ${feedUrl}:`, feedErr.message);
        }
      }
    }

    saveFeedsConfig(config);
  } catch (error) {
    console.error('Error in checkFeedsAndBroadcast:', error);
  } finally {
    isChecking = false;
  }
}
