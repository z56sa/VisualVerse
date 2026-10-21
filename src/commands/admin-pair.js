import { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder, MessageFlags } from 'discord.js';
import dbService from '../services/database.js';
import embedUtils from '../utils/embedBuilder.js';

export const adminPairCommand = {
  data: new SlashCommandBuilder()
    .setName('admin-pair')
    .setDescription('إدارة وتخزين ثنائيات الصور والبنرات المتناسقة في قاعدة البيانات')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addSubcommand(subcommand =>
      subcommand
        .setName('add')
        .setDescription('إضافة ثنائي جديد (افتار + بنر)')
        .addStringOption(opt =>
          opt.setName('title')
            .setDescription('عنوان أو وصف الثنائي (مثال: Naruto & Hinata / Cyber Aesthetic)')
            .setRequired(true)
        )
        .addStringOption(opt =>
          opt.setName('category')
            .setDescription('فئة الثنائي')
            .setRequired(true)
            .addChoices(
              { name: '🎌 أنمي (Anime)', value: 'anime' },
              { name: '👩‍❤️‍👨 ثنائيات كبلز (Couples)', value: 'couples' },
              { name: '✨ جمالي وفخم (Aesthetic)', value: 'aesthetic' },
              { name: '🎮 ألعاب وجيمينج (Gaming)', value: 'gaming' }
            )
        )
        .addStringOption(opt =>
          opt.setName('avatar_url')
            .setDescription('رابط صورة الافتار (Avatar URL)')
            .setRequired(true)
        )
        .addStringOption(opt =>
          opt.setName('banner_url')
            .setDescription('رابط صورة البنر/الهيدر (Banner URL)')
            .setRequired(true)
        )
        .addStringOption(opt =>
          opt.setName('source')
            .setDescription('المصدر أو اسم الرسام (اختياري)')
            .setRequired(false)
        )
    )
    .addSubcommand(subcommand =>
      subcommand
        .setName('stats')
        .setDescription('عرض إحصائيات الثنائيات المخزنة وعدد كل فئة')
    )
    .addSubcommand(subcommand =>
      subcommand
        .setName('delete')
        .setDescription('حذف ثنائي محدد بواسطة الرقم التعريفي (ID)')
        .addIntegerOption(opt =>
          opt.setName('id')
            .setDescription('معرف الثنائي (ID)')
            .setRequired(true)
        )
    ),

  async execute(interaction) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });

    const subcommand = interaction.options.getSubcommand();

    if (subcommand === 'add') {
      const title = interaction.options.getString('title');
      const category = interaction.options.getString('category');
      const avatarUrl = interaction.options.getString('avatar_url');
      const bannerUrl = interaction.options.getString('banner_url');
      const source = interaction.options.getString('source') || interaction.user.tag;

      // Validate URLs
      const urlPattern = /^https?:\/\/.+/i;
      if (!urlPattern.test(avatarUrl) || !urlPattern.test(bannerUrl)) {
        return interaction.editReply({
          embeds: [embedUtils.error('روابط غير صالحة', 'يرجى التأكد من إدخال روابط صحيحة تبدأ بـ http:// أو https://')]
        });
      }

      try {
        const { id } = dbService.addPair({
          title,
          category,
          avatar_url: avatarUrl,
          banner_url: bannerUrl,
          source
        });

        const embed = new EmbedBuilder()
          .setColor(embedUtils.colors.success)
          .setTitle('✅ تم حفظ الثنائي بنجاح!')
          .setDescription(
            `🆔 **المعرف:** \`#${id}\`\n` +
            `📌 **العنوان:** **${title}**\n` +
            `📁 **الفئة:** \`${category.toUpperCase()}\`\n` +
            `👤 **المصدر:** ${source}`
          )
          .setThumbnail(avatarUrl)
          .setImage(bannerUrl)
          .setTimestamp();

        return interaction.editReply({ embeds: [embed] });
      } catch (err) {
        console.error('Error adding pair:', err);
        return interaction.editReply({
          embeds: [embedUtils.error('فشل الإضافة', `حدث خطأ أثناء الحفظ في قاعدة البيانات: ${err.message}`)]
        });
      }
    }

    if (subcommand === 'stats') {
      const stats = dbService.getStats();

      let desc = `📊 **إجمالي الثنائيات المخزنة:** \`${stats.total}\`\n\n**توزيع الفئات:**\n`;
      if (stats.categories.length === 0) {
        desc += '*لا توجد عناصر بعد.*';
      } else {
        for (const cat of stats.categories) {
          desc += `• \`${cat.category}\`: **${cat.count}** ثنائيات\n`;
        }
      }

      const embed = new EmbedBuilder()
        .setColor(embedUtils.colors.primary)
        .setTitle('📁 إحصائيات معرض VisualVerse')
        .setDescription(desc)
        .setTimestamp();

      return interaction.editReply({ embeds: [embed] });
    }

    if (subcommand === 'delete') {
      const id = interaction.options.getInteger('id');
      const success = dbService.deletePair(id);

      if (success) {
        return interaction.editReply({
          embeds: [embedUtils.success('تم الحذف', `تم حذف الثنائي ذو المعرف \`#${id}\` بنجاح.`)]
        });
      } else {
        return interaction.editReply({
          embeds: [embedUtils.error('غير موجود', `لم يتم العثور على ثنائي يحمل المعرف \`#${id}\`.`)]
        });
      }
    }
  }
};

export default adminPairCommand;
