import { SlashCommandBuilder, EmbedBuilder } from 'discord.js';
import { fetchFeedItems, DEFAULT_FEEDS } from '../services/feedService.js';
import { generateDailyRecapWithLang } from '../services/aiService.js';
import { loadFeedsConfig } from '../services/storageService.js';

export const dailyRecapCommand = {
  data: new SlashCommandBuilder()
    .setName('daily-recap')
    .setDescription('Generate a smart AI daily news summary | توليد ملخص ذكي لأبرز أخبار اليوم'),

  async execute(interaction, geminiApiKey) {
    await interaction.deferReply();

    const config = loadFeedsConfig();
    const guildConfig = config[interaction.guildId];
    
    // إذا لم تكن لغة السيرفر مضبوطة بالإنجليزية صراحة، الافتراضي هو العربية الفصحى دائماً
    const lang = (guildConfig?.language === 'en') ? 'en' : 'ar';
    const isArabic = lang === 'ar';

    const feedsToScan = (guildConfig && guildConfig.feeds?.length > 0)
      ? guildConfig.feeds
      : DEFAULT_FEEDS.map(f => f.url);

    try {
      const allNews = [];

      for (const url of feedsToScan.slice(0, 3)) {
        try {
          const feed = await fetchFeedItems(url, 2);
          for (const item of feed.items) {
            allNews.push({
              title: item.title,
              source: feed.feedTitle,
              content: item.contentSnippet || ''
            });
          }
        } catch (err) {
          console.warn('[DailyRecap] Skipping feed:', err.message);
        }
      }

      if (allNews.length === 0) {
        await interaction.editReply({
          content: isArabic
            ? '⚠️ لا توجد أخبار كافية لتوليد حصاد اليوم. تأكد من ضبط مصادر RSS عبر `/setup-feed`.'
            : '⚠️ No news items found. Make sure RSS feeds are configured via `/setup-feed`.'
        });
        return;
      }

      // استدعاء محرك التلخيص والترجمة
      const recapText = await generateDailyRecapWithLang(geminiApiKey, allNews, lang);

      const recapEmbed = new EmbedBuilder()
        .setColor(0x5865F2)
        .setTitle(isArabic ? '⚡ حصاد FeedPulse الإخباري اليومي' : '⚡ FeedPulse Daily News Highlights')
        .setDescription(recapText)
        .addFields({
          name: isArabic ? '📡 المصادر المستخدمة' : '📡 Sources',
          value: [...new Set(allNews.map(n => n.source))].join(' • ') || 'RSS Feeds',
          inline: false
        })
        .setFooter({
          text: isArabic ? 'FeedPulse • تلخيص يومي بالذكاء الاصطناعي' : 'FeedPulse • AI-Powered Daily Summary'
        })
        .setTimestamp();

      await interaction.editReply({ content: null, embeds: [recapEmbed] });

    } catch (err) {
      console.error('[DailyRecap] Error:', err);
      await interaction.editReply({
        content: isArabic
          ? `❌ حدث خطأ أثناء توليد الملخص: \`${err.message}\``
          : `❌ Error generating recap: \`${err.message}\``
      });
    }
  }
};
