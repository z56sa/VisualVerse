import os
import sys
import json
import random
import asyncio
import aiohttp
from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# تحميل المتغيرات البيئية
load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_TOKEN")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY", "")
PORT = int(os.getenv("PORT", 8080))


async def run_web_server():
    """خادم ويب خفيف لإبقاء الخدمة نشطة على Render"""
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="TwinAura Matching Bot is Online!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 خادم الويب يعمل على المنفذ: {PORT}")


# الفئات المحددة مسبقاً للبحث عن الأفاتار والبنر المتناسقين
CATEGORIES = {
    "أنمي": {
        "unsplash": "matching anime aesthetic",
        "booru_avatar": "1girl solo aesthetic rating:general",
        "booru_banner": "scenery aesthetic sky wallpaper rating:general"
    },
    "استاتيك": {
        "unsplash": "minimalist aesthetic matching profile",
        "booru_avatar": "aesthetic solo rating:general",
        "booru_banner": "scenery lofi aesthetic wallpaper rating:general"
    },
    "داكن": {
        "unsplash": "dark gothic purple aesthetic",
        "booru_avatar": "dark purple_theme solo rating:general",
        "booru_banner": "scenery dark purple_theme wallpaper rating:general"
    },
    "لطيف": {
        "unsplash": "cute pastel aesthetic anime",
        "booru_avatar": "cute 1girl pastel rating:general",
        "booru_banner": "pastel scenery clouds wallpaper rating:general"
    }
}


async def fetch_matching_pairs(category: str, limit: int = 10) -> list[dict]:
    """
    جلب أزواج متناسقة (أفاتار + بنر).
    إذا كان مفتاح Unsplash متوفراً، يجلب منه.
    إذا لم يكن متوفراً، يجلب أزواجاً حقيقية عالية الدقة HD مباشرة بدون الحاجة لمفتاح.
    """
    cat_cfg = CATEGORIES.get(category, CATEGORIES["أنمي"])
    pairs = []

    # 1. تجربة Unsplash إذا تم توفير المفتاح
    if UNSPLASH_API_KEY and UNSPLASH_API_KEY != "YOUR_UNSPLASH_API_KEY":
        query = cat_cfg["unsplash"]
        url = f"https://api.unsplash.com/search/photos?query={query}&client_id={UNSPLASH_API_KEY}&per_page={limit*2}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        for i in range(0, len(results) - 1, 2):
                            avatar_url = results[i]["urls"]["regular"]
                            banner_url = results[i+1]["urls"]["regular"]
                            pairs.append({"avatar": avatar_url, "banner": banner_url})
                        if pairs:
                            return pairs
        except Exception as e:
            print(f"[Unsplash fallback]: {e}")

    # 2. المصدر الاحتياطي المباشر عالي الدقة HD (بدون الحاجة لمفتاح API)
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0"}
            pid_avatar = random.randint(0, 4)
            pid_banner = random.randint(0, 4)

            url_avatars = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&tags={'+'.join(cat_cfg['booru_avatar'].split())}&limit={limit}&pid={pid_avatar}"
            url_banners = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&tags={'+'.join(cat_cfg['booru_banner'].split())}&limit={limit}&pid={pid_banner}"

            async with session.get(url_avatars, headers=headers) as r_av, session.get(url_banners, headers=headers) as r_bn:
                if r_av.status == 200 and r_bn.status == 200:
                    text_av = await r_av.text()
                    text_bn = await r_bn.text()
                    data_av = json.loads(text_av) if text_av.strip() else []
                    data_bn = json.loads(text_bn) if text_bn.strip() else []

                    min_len = min(len(data_av), len(data_bn))
                    for i in range(min_len):
                        item_a = data_av[i]
                        item_b = data_bn[i]
                        av_file = str(item_a.get("image", ""))
                        bn_file = str(item_b.get("image", ""))
                        if not av_file.lower().endswith(".gif") and not bn_file.lower().endswith(".gif"):
                            av_url = f"https://safebooru.org/images/{item_a['directory']}/{av_file}"
                            bn_url = f"https://safebooru.org/images/{item_b['directory']}/{bn_file}"
                            pairs.append({"avatar": av_url, "banner": bn_url})
    except Exception as e:
        print(f"[Matching fetch error]: {e}")

    return pairs


# ==================== كلاس الأزرار التفاعلية (Pagination) ====================
class MatchingView(discord.ui.View):
    def __init__(self, pairs: list[dict], category: str):
        super().__init__(timeout=180)
        self.pairs = pairs
        self.category = category
        self.index = 0
        self.update_button_states()

    def update_button_states(self):
        # تمكين أو تعطيل أزرار التنقل
        self.prev_button.disabled = (self.index == 0)
        self.next_button.disabled = (self.index >= len(self.pairs) - 1)

    def update_embed(self) -> discord.Embed:
        pair = self.pairs[self.index]
        embed = discord.Embed(
            title="✨ أفاتار وبنر متناسقين (Matching Set)",
            description=f"الفئة: **{self.category}** • عرض الزوج **{self.index + 1}** من أصل **{len(self.pairs)}**\n"
                        f"*(الأفاتار في الصورة المصغرة والبنر في الصورة الكبيرة)*",
            color=discord.Color.from_rgb(114, 137, 218)
        )
        embed.set_thumbnail(url=pair.get("avatar"))
        embed.set_image(url=pair.get("banner"))
        embed.add_field(name="🖼️ تحميل الأفاتار", value=f"[اضغط هنا]({pair.get('avatar')})", inline=True)
        embed.add_field(name="🌆 تحميل البنر", value=f"[اضغط هنا]({pair.get('banner')})", inline=True)
        embed.set_footer(text="TwinAura Bot • Matching Profiles • جودة عالية HD")
        return embed

    @discord.ui.button(label="السابق", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            self.update_button_states()
            await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="التالي", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pairs) - 1:
            self.index += 1
            self.update_button_states()
            await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="إغلاق", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


# ==================== إعدادات البوت الأساسية ====================
class TwinAuraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            await run_web_server()
        except Exception as e:
            print(f"⚠️ تنبيه خادم الويب: {e}")
        try:
            synced = await self.tree.sync()
            print(f"✅ تم مزامنة {len(synced)} أمر سلاش تفاعلي بنجاح.")
        except Exception as e:
            print(f"❌ خطأ أثناء المزامنة: {e}")


bot = TwinAuraBot()


@bot.event
async def on_ready():
    print(f"🤖 البوت يعمل الآن بنجاح باسم: {bot.user.name}")


# ==================== أمر الـ Slash Command الرئيسي ====================
@bot.tree.command(name="matching", description="جلب أفاتار وبنر متناسقين للملف الشخصي بحسب الفئة")
@app_commands.describe(category="اختر الفئة المطلوبة")
@app_commands.choices(category=[
    app_commands.Choice(name="أنمي", value="أنمي"),
    app_commands.Choice(name="استاتيك", value="استاتيك"),
    app_commands.Choice(name="داكن", value="داكن"),
    app_commands.Choice(name="لطيف", value="لطيف")
])
async def matching_command(interaction: discord.Interaction, category: str):
    await interaction.response.defer(thinking=True)

    pairs = await fetch_matching_pairs(category, limit=10)

    if not pairs:
        await interaction.followup.send("⚠️ لم يتم العثور على أزواج متناسقة حالياً. يرجى المحاولة مرة أخرى.", ephemeral=True)
        return

    view = MatchingView(pairs, category)
    embed = view.update_embed()
    await interaction.followup.send(embed=embed, view=view)


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ خطأ: لم يتم العثور على DISCORD_TOKEN في ملف .env")
    else:
        bot.run(BOT_TOKEN)
