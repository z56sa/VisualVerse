import { SlashCommandBuilder } from 'discord.js';
import embedUtils from '../utils/embedBuilder.js';

export const getMediaCommand = {
  data: new SlashCommandBuilder()
    .setName('get-media')
    .setDescription('جلب وتنزيل الافتار والبنر الخاص بأي مستخدم بجودة عالية 1024px')
    .addUserOption(option =>
      option.setName('target')
        .setDescription('المستخدم المراد جلب وسائطه (منشن أو كتابة)')
        .setRequired(false)
    )
    .addStringOption(option =>
      option.setName('user_id')
        .setDescription('معرف المستخدم (User ID) في حال لم يكن متواجداً في السيرفر')
        .setRequired(false)
    ),

  async execute(interaction) {
    await interaction.deferReply();

    const targetUserOption = interaction.options.getUser('target');
    const targetUserId = interaction.options.getString('user_id');

    let targetId = targetUserOption ? targetUserOption.id : null;

    if (!targetId && targetUserId) {
      targetId = targetUserId.trim();
    }

    // Default to the interaction author if no user specified
    if (!targetId) {
      targetId = interaction.user.id;
    }

    try {
      // Force fetch user to get banner and accent color
      const fetchedUser = await interaction.client.users.fetch(targetId, { force: true });

      if (!fetchedUser) {
        return interaction.editReply({
          embeds: [embedUtils.error('خطأ', 'لم يتم العثور على المستخدم بالمعرف المحدد.')]
        });
      }

      const { embed, row } = embedUtils.createUserMediaEmbed(fetchedUser, fetchedUser);

      await interaction.editReply({
        embeds: [embed],
        components: [row]
      });
    } catch (err) {
      console.error('Error in get-media:', err);
      await interaction.editReply({
        embeds: [
          embedUtils.error(
            'تعذر جلب بيانات المستخدم',
            `تأكد من صحة معرف المستخدم (User ID). الخطأ: ${err.message}`
          )
        ]
      });
    }
  }
};

export default getMediaCommand;
