import os
import sys
import aiohttp
from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 8080))


async def run_web_server():
    """خادم ويب خفيف لإبقاء الخدمة نشطة ومتوافقة مع Render"""
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="VisualVerse Discord Avatar & Banner Fetcher is Online!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 خادم الويب يعمل على المنفذ: {PORT}")


# تفعيل الصلاحيات اللازمة لقراءة الأعضاء
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


class UserAvatarBannerView(discord.ui.View):
    """
    أزرار تفاعلية للتبديل بين صورة الحساب وصورة السيرفر والبنر ورابط التحميل.
    """
    def __init__(self, target_user: discord.User, member: discord.Member | None, requester: discord.User | discord.Member):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.member = member
        self.requester = requester

        # إذا لم يكن لديه افتار مخصص في السيرفر، نعطل الزر الخاص به
        if not member or not member.guild_avatar:
            self.btn_guild_avatar.disabled = True

        # إذا لم يكن لديه بنر، نعطل زر البنر
        if not target_user.banner:
            self.btn_banner.disabled = True

    def create_avatar_embed(self) -> discord.Embed:
        avatar_url = self.target_user.display_avatar.url
        embed = discord.Embed(
            title=f"👤 افتار: {self.target_user.display_name}",
            description=f"**[🔗 تحميل الصورة بجودة عالية PNG/JPG]({avatar_url})**",
            color=discord.Color.blue()
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(
            text=f"تم الطلب بواسطة {self.requester.display_name} • معرف المستخدم: {self.target_user.id}",
            icon_url=self.requester.display_avatar.url
        )
        return embed

    def create_guild_avatar_embed(self) -> discord.Embed:
        guild_avatar_url = self.member.guild_avatar.url if self.member and self.member.guild_avatar else self.target_user.display_avatar.url
        embed = discord.Embed(
            title=f"🛡️ افتار السيرفر: {self.target_user.display_name}",
            description=f"**[🔗 تحميل افتار السيرفر بجودة عالية]({guild_avatar_url})**",
            color=discord.Color.purple()
        )
        embed.set_image(url=guild_avatar_url)
        embed.set_footer(
            text=f"تم الطلب بواسطة {self.requester.display_name}",
            icon_url=self.requester.display_avatar.url
        )
        return embed

    def create_banner_embed(self) -> discord.Embed:
        banner_url = self.target_user.banner.url if self.target_user.banner else None
        embed = discord.Embed(
            title=f"🖼️ بنر بروفايل: {self.target_user.display_name}",
            description=f"**[🔗 تحميل البنر بجودة عالية]({banner_url})**" if banner_url else "لا يوجد بنر لهذا الحساب",
            color=discord.Color.gold()
        )
        if banner_url:
            embed.set_image(url=banner_url)
        embed.set_footer(
            text=f"تم الطلب بواسطة {self.requester.display_name}",
            icon_url=self.requester.display_avatar.url
        )
        return embed

    @discord.ui.button(label="👤 افتار الحساب", style=discord.ButtonStyle.primary, custom_id="btn_avatar")
    async def btn_avatar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_avatar_embed(), view=self)

    @discord.ui.button(label="🛡️ افتار السيرفر", style=discord.ButtonStyle.secondary, custom_id="btn_guild_avatar")
    async def btn_guild_avatar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_guild_avatar_embed(), view=self)

    @discord.ui.button(label="🖼️ بنر الحساب", style=discord.ButtonStyle.success, custom_id="btn_banner")
    async def btn_banner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_banner_embed(), view=self)

    @discord.ui.button(label="🗑️ إغلاق", style=discord.ButtonStyle.danger, custom_id="btn_close")
    async def btn_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("❌ هذا الزر مخصص لصاحب الطلب فقط!", ephemeral=True)
            return
        await interaction.message.delete()


@bot.event
async def on_ready():
    try:
        await run_web_server()
    except Exception as e:
        print(f"⚠️ تنبيه خادم الويب: {e}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ تم تسجيل ومزامنة {len(synced)} أمر سلاش بنجاح.")
    except Exception as e:
        print(f"❌ خطأ أثناء مزامنة الأوامر: {e}")
    print(f"🤖 البوت جاهز باسم: {bot.user}")


# أمر عرض افتار المستخدم (الشخص نفسه أو شخص آخر بالمنشن)
@bot.tree.command(name="avatar", description="عرض وتحميل صورة الافتار (Avatar) لحسابك أو لأي شخص بالمنشن كصورة ثابتة بدقة كاملة")
@app_commands.describe(user="الشخص الذي تريد سرقة/عرض افتاره (اتركه فارغاً لعرض افتارك أنت)")
async def slash_avatar(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.defer()

    # جلب بيانات المستخدم الكاملة مع البنر
    try:
        full_user = await bot.fetch_user(target.id)
    except Exception:
        full_user = target

    member = interaction.guild.get_member(target.id) if interaction.guild else None

    view = UserAvatarBannerView(target_user=full_user, member=member, requester=interaction.user)
    await interaction.followup.send(embed=view.create_avatar_embed(), view=view)


# أمر عرض بنر المستخدم (الشخص نفسه أو شخص آخر بالمنشن)
@bot.tree.command(name="banner", description="عرض وتحميل بنر البروفايل (Banner) لحسابك أو لأي شخص بالمنشن كصورة بدقة كاملة")
@app_commands.describe(user="الشخص الذي تريد عرض بنره (اتركه فارغاً لعرض بنرك أنت)")
async def slash_banner(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.defer()

    try:
        full_user = await bot.fetch_user(target.id)
    except Exception:
        full_user = target

    if not full_user.banner:
        await interaction.followup.send(f"⚠️ المستخدم **{full_user.display_name}** ليس لديه بنر بروفايل مخصص (أو لم يقم بوضع بنر).", ephemeral=True)
        return

    member = interaction.guild.get_member(target.id) if interaction.guild else None

    view = UserAvatarBannerView(target_user=full_user, member=member, requester=interaction.user)
    await interaction.followup.send(embed=view.create_banner_embed(), view=view)


# أمر البروفايل الكامل (يعرض الافتار والبنر معاً)
@bot.tree.command(name="profile", description="عرض بروفايل الشخص بالكامل مع الافتار والبنر الخاص به")
@app_commands.describe(user="الشخص المطلوب (اتركه فارغاً لعرض بروفايلك)")
async def slash_profile(interaction: discord.Interaction, user: discord.User = None):
    await slash_avatar.callback(interaction, user)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ خطأ: يرجى وضع DISCORD_TOKEN في ملف .env")
    else:
        bot.run(DISCORD_TOKEN)
