import { SlashCommandBuilder } from 'discord.js';
import { fetchFeedItems, DEFAULT_FEEDS } from '../services/feedService.js';
import { summarizeNewsItem } from '../services/aiService.js';
import { createNewsEmbed, createNewsActionRow } from '../utils/embedBuilder.js';
import { loadFeedsConfig } from '../services/storageService.js';

export const latestNewsCommand = {
  data: new SlashCommandBuilder()
    .setName('latest-news')
    .setDescription('جلب وتلخيص أحدث 3 أخبار فوراً بالذكاء الاصطناعي (بالعربية أو الإنجليزية)')
    .addStringOption(option =>
      option
        .setName('category')
        .setDescription('اختر تصنيف الأخبار')
        .addChoices(
          { name: '🎮 ألعاب (IGN Gaming)', value: 'gaming' },
          { name: '💻 تكنولوجيا (The Verge Tech)', value: 'tech' },
          { name: '🌸 أنمي (Anime News Network)', value: 'anime' }
        )
    )
    .addStringOption(option =>
      option
        .setName('language')
        .setDescription('اختر لغة التلخيص')
        .addChoices(
          { name: '🇸🇦 العربية (Arabic)', value: 'ar' },
          { name: '🇺🇸 English (الإنجليزية)', value: 'en' }
        )
    ),

  async execute(interaction, geminiApiKey) {
    await interaction.deferReply();

    const category = interaction.options.getString('category');
    const selectedLang = interaction.options.getString('language');
    const config = loadFeedsConfig();
    const guildConfig = config[interaction.guildId];

    // اللغة: إما المختارة بالأمر أو المضبوطة بالسيرفر أو الافتراضي 'ar'
    const lang = selectedLang || guildConfig?.language || 'ar';
    const isArabic = lang === 'ar';

    let targetFeedUrl = null;
    if (category) {
      const found = DEFAULT_FEEDS.find(f => f.category === category);
      if (found) targetFeedUrl = found.url;
    } else {
      const guildFeeds = guildConfig?.feeds;
      if (guildFeeds && guildFeeds.length > 0) {
        targetFeedUrl = guildFeeds[0];
      } else {
        targetFeedUrl = DEFAULT_FEEDS[0].url;
      }
    }

    try {
      const feedData = await fetchFeedItems(targetFeedUrl, 3);
      if (!feedData.items || feedData.items.length === 0) {
        await interaction.editReply({
          content: isArabic ? '⚠️ لم يتم العثور على أي أخبار حالياً في المصدر.' : '⚠️ No news items found currently in this feed.'
        });
        return;
      }

      await interaction.editReply({
        content: isArabic
          ? `⚡ **جاري معالجة وتلخيص الأخبار من: ${feedData.feedTitle}...**`
          : `⚡ **Processing and summarizing news from: ${feedData.feedTitle}...**`
      });

      for (let i = 0; i < feedData.items.length; i++) {
        const item = feedData.items[i];
        const aiResult = await summarizeNewsItem(geminiApiKey, item.title, item.contentSnippet, lang);

        const embed = createNewsEmbed({
          title: aiResult.formattedTitle,
          summaryPoints: aiResult.summaryPoints,
          link: item.link,
          imageUrl: item.imageUrl,
          pubDate: item.pubDate,
          sourceName: feedData.feedTitle,
          lang
        });

        const row = createNewsActionRow(item.link, lang);

        if (i === 0) {
          await interaction.editReply({ content: null, embeds: [embed], components: [row] });
        } else {
          await interaction.followUp({ embeds: [embed], components: [row] });
        }
      }
    } catch (err) {
      await interaction.editReply({
        content: isArabic ? `❌ تعذر جلب الأخبار: \`${err.message}\`` : `❌ Could not fetch news: \`${err.message}\``
      });
    }
  }
};
