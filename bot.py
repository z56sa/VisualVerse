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

# تحميل المتغيرات البيئية من ملف .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY", "OB88UtIkWu8ebwwNPlZPLkVEkCmmQU9n")
PORT = int(os.getenv("PORT", 8080))


async def run_web_server():
    """خادم ويب خفيف لإبقاء الخدمة نشطة ومتوافقة مع Render Web Service"""
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="VisualVerse Profile Aesthetics Bot is Online!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 خادم الويب يعمل على المنفذ: {PORT}")


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# تصنيفات مخصصة للافتار والبنر
AVATAR_CATEGORIES = {
    "anime_boy": {"label": "أنمي أولاد (Anime Boy)", "query": "anime boy pfp avatar aesthetic", "color": discord.Color.blue(), "emoji": "👦"},
    "anime_girl": {"label": "أنمي بنات (Anime Girl)", "query": "anime girl pfp avatar aesthetic", "color": discord.Color.purple(), "emoji": "👧"},
    "cyberpunk": {"label": "سايبربانك ونيون (Cyberpunk/Neon)", "query": "cyberpunk neon pfp avatar", "color": discord.Color.teal(), "emoji": "🌆"},
    "dark_aesthetic": {"label": "دارك وبلاك (Dark/Goth)", "query": "dark aesthetic pfp grunge emo", "color": discord.Color.dark_grey(), "emoji": "🖤"},
    "gaming": {"label": "ألعاب (Gaming/Gamer)", "query": "gamer gaming avatar pfp icon", "color": discord.Color.gold(), "emoji": "🎮"},
    "matching": {"label": "افتارات طقم (Matching/Couple)", "query": "matching pfp anime couple", "color": discord.Color.fuchsia(), "emoji": "✨"},
    "cats": {"label": "قطط كيوت (Cats/Cute)", "query": "cute cat pfp icon meme", "color": discord.Color.orange(), "emoji": "🐱"}
}

BANNER_CATEGORIES = {
    "anime_banner": {"label": "بنرات أنمي (Anime Banners)", "query": "anime discord banner aesthetic header", "color": discord.Color.magenta(), "emoji": "🌸"},
    "dark_purple": {"label": "بنرات بنفسجي ودارك (Purple / Dark)", "query": "purple dark discord banner aesthetic header", "color": discord.Color.purple(), "emoji": "🌌"},
    "cyberpunk_banner": {"label": "بنرات سايبربانك (Cyberpunk / Retro)", "query": "cyberpunk synthwave banner header discord", "color": discord.Color.teal(), "emoji": "🌆"},
    "nature_lofi": {"label": "طبيعة ولوفاي (Nature / Lofi)", "query": "lofi pixel nature landscape banner header discord", "color": discord.Color.green(), "emoji": "🌿"},
    "gaming_banner": {"label": "ألعاب وجيمينج (Gaming Banners)", "query": "gaming discord banner header aesthetic", "color": discord.Color.gold(), "emoji": "🎮"},
    "minimal_glitch": {"label": "غليتش ومينيمال (Glitch / Minimal)", "query": "glitch aesthetic banner header discord", "color": discord.Color.dark_teal(), "emoji": "⚡"}
}


async def fetch_media(query: str, limit: int = 15) -> list[dict]:
    """
    جلب الـ GIFs والصور عبر Giphy API.
    """
    url = "https://api.giphy.com/v1/gifs/search"
    params = {
        "api_key": GIPHY_API_KEY,
        "q": query,
        "limit": limit,
        "rating": "pg-13",
        "lang": "en"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("data", [])
                    extracted = []
                    for item in results:
                        images = item.get("images", {})
                        orig = images.get("original") or images.get("downsized_medium") or images.get("fixed_height")
                        if orig and orig.get("url"):
                            extracted.append({
                                "url": orig["url"],
                                "title": item.get("title") or query
                            })
                    return extracted
                else:
                    return []
    except Exception as e:
        print(f"Error fetching media: {e}")
        return []


class ProfileMediaPaginationView(discord.ui.View):
    """
    عرض البنرات والافتارات بأزرار التنقل وتحميل الصورة.
    """
    def __init__(self, items: list[dict], title: str, media_type: str, color: discord.Color, user: discord.User | discord.Member):
        super().__init__(timeout=180)
        self.items = items
        self.title = title
        self.media_type = media_type
        self.color = color
        self.user = user
        self.index = 0
        self.update_buttons()

    def update_buttons(self):
        self.btn_prev.disabled = (self.index == 0)
        self.btn_next.disabled = (self.index >= len(self.items) - 1)

    def create_embed(self) -> discord.Embed:
        current = self.items[self.index]
        icon = "👤" if self.media_type == "avatar" else "🖼️"
        embed = discord.Embed(
            title=f"{icon} {self.title}",
            description=f"[🔗 رابط مباشر بدقة عالية]({current['url']})",
            color=self.color
        )
        embed.set_image(url=current["url"])
        embed.set_footer(
            text=f"النموذج {self.index + 1} من {len(self.items)} • تم الطلب بواسطة {self.user.display_name}",
            icon_url=self.user.display_avatar.url
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ هذه الأزرار خاصة بصاحب الطلب فقط!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀️ السابق", style=discord.ButtonStyle.secondary, custom_id="btn_prev")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="التالي ▶️", style=discord.ButtonStyle.primary, custom_id="btn_next")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.items) - 1:
            self.index += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="🗑️ إغلاق", style=discord.ButtonStyle.danger, custom_id="btn_delete")
    async def btn_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True


class CategorySelect(discord.ui.Select):
    def __init__(self, categories_dict: dict, media_type: str, user: discord.User | discord.Member):
        self.categories_dict = categories_dict
        self.media_type = media_type
        self.user = user

        options = [
            discord.SelectOption(
                label=data["label"],
                value=k,
                emoji=data["emoji"]
            )
            for k, data in categories_dict.items()
        ]
        placeholder = "اختر ستايل الافتار (Avatar PFP)..." if media_type == "avatar" else "اختر ستايل البنر (Discord Banner)..."
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ هذه القائمة خاصة بصاحب الطلب فقط!", ephemeral=True)
            return

        selected_key = self.values[0]
        cat_data = self.categories_dict[selected_key]

        await interaction.response.defer()

        items = await fetch_media(cat_data["query"], limit=15)
        if not items:
            await interaction.followup.send("⚠️ لم يتم العثور على نتائج متناسقة حالياً.", ephemeral=True)
            return

        view = ProfileMediaPaginationView(
            items=items,
            title=cat_data["label"],
            media_type=self.media_type,
            color=cat_data["color"],
            user=self.user
        )
        await interaction.edit_original_response(embed=view.create_embed(), view=view)


class CategorySelectView(discord.ui.View):
    def __init__(self, categories_dict: dict, media_type: str, user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories_dict=categories_dict, media_type=media_type, user=user))


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
    print(f"🤖 البوت جاهز ويعمل باسم: {bot.user}")


# أمر جلب وتصفح الافتارات
@bot.tree.command(name="avatar", description="تصفح افتارات (PFP) فخمة ومتحركة للبروفايل بحسب التصنيف أو بالبحث")
@app_commands.describe(query="كلمة للبحث (اختياري، اتركه فارغاً لعرض قائمة التصنيفات الفخمة)")
async def slash_avatar(interaction: discord.Interaction, query: str = None):
    if query:
        await interaction.response.defer()
        full_query = f"{query} pfp avatar aesthetic"
        items = await fetch_media(full_query, limit=15)
        if not items:
            await interaction.followup.send(f"⚠️ لم يتم العثور على افتارات لكلمة: **{query}**", ephemeral=True)
            return
        view = ProfileMediaPaginationView(
            items=items,
            title=f"افتارات: {query}",
            media_type="avatar",
            color=discord.Color.blue(),
            user=interaction.user
        )
        await interaction.followup.send(embed=view.create_embed(), view=view)
    else:
        embed = discord.Embed(
            title="👤 اختر تصنيف الافتار (Discord Avatar / PFP)",
            description="اختر إحدى الفئات من القائمة بالأسفل لتصفح افتارات متناسقة لبروفايلك:",
            color=discord.Color.blurple()
        )
        view = CategorySelectView(categories_dict=AVATAR_CATEGORIES, media_type="avatar", user=interaction.user)
        await interaction.response.send_message(embed=embed, view=view)


# أمر جلب وتصفح البنرات
@bot.tree.command(name="banner", description="تصفح بنرات (Banners) فخمة ومتحركة للبروفايل بحسب التصنيف أو بالبحث")
@app_commands.describe(query="كلمة للبحث (اختياري، اتركه فارغاً لعرض قائمة التصنيفات الفخمة)")
async def slash_banner(interaction: discord.Interaction, query: str = None):
    if query:
        await interaction.response.defer()
        full_query = f"{query} banner header aesthetic discord"
        items = await fetch_media(full_query, limit=15)
        if not items:
            await interaction.followup.send(f"⚠️ لم يتم العثور على بنرات لكلمة: **{query}**", ephemeral=True)
            return
        view = ProfileMediaPaginationView(
            items=items,
            title=f"بنرات: {query}",
            media_type="banner",
            color=discord.Color.purple(),
            user=interaction.user
        )
        await interaction.followup.send(embed=view.create_embed(), view=view)
    else:
        embed = discord.Embed(
            title="🖼️ اختر تصنيف البنر (Discord Profile Banner)",
            description="اختر إحدى الفئات من القائمة بالأسفل لتصفح بنرات وهيدرات متناسقة لبروفايلك:",
            color=discord.Color.dark_purple()
        )
        view = CategorySelectView(categories_dict=BANNER_CATEGORIES, media_type="banner", user=interaction.user)
        await interaction.response.send_message(embed=embed, view=view)


# أمر مساعدة عام
@bot.tree.command(name="help", description="عرض أوامر البوت وطريقة الاستخدام")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ دليل أوامر VisualVerse",
        description="بوت مخصص لجلب أحدث وأفخم الافتارات والبنرات المتناسقة لحسابك على ديسكورد:",
        color=discord.Color.gold()
    )
    embed.add_field(name="👤 `/avatar`", value="تصفح تصنيفات الافتارات الفخمة (أنمي أولاد/بنات، دارك، سايبربانك، أطقم، قطط) أو ابحث مباشرة `/avatar query:اسم`.", inline=False)
    embed.add_field(name="🖼️ `/banner`", value="تصفح بنرات وهيدرات ديسكورد المتحركة والجمالية (أنمي، بنفسجي ودارك، نيون، لوفاي) أو ابحث مباشرة `/banner query:اسم`.", inline=False)
    embed.set_footer(text="جميع النتائج تحتوي على أزرار تقليب ◀️ ▶️ ورابط مباشر بجودة عالية.")
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ خطأ: يرجى وضع DISCORD_TOKEN في ملف .env")
    else:
        bot.run(DISCORD_TOKEN)
