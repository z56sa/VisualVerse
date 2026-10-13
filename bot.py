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
TENOR_API_KEY = os.getenv("TENOR_API_KEY")
TENOR_CLIENT_KEY = os.getenv("TENOR_CLIENT_KEY", "discord_gif_bot")
PORT = int(os.getenv("PORT", 8080))


async def run_web_server():
    """خادم ويب خفيف لإبقاء الخدمة نشطة ومتوافقة مع Render Web Service"""
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="Bot is running online!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 خادم الويب يعمل على المنفذ: {PORT}")


# إعداد الصلاحيات (Intents)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# الفئات المحددة مسبقاً مع الكلمات المفتاحية والألوان
CATEGORIES = {
    "gaming": {
        "label": "ألعاب (Gaming)",
        "query": "gaming video games",
        "color": discord.Color.purple(),
        "emoji": "🎮"
    },
    "anime": {
        "label": "أنمي (Anime)",
        "query": "anime aesthetic",
        "color": discord.Color.magenta(),
        "emoji": "🌸"
    },
    "nature": {
        "label": "طبيعة (Nature)",
        "query": "nature landscape aesthetics",
        "color": discord.Color.green(),
        "emoji": "🌿"
    },
    "memes": {
        "label": "ميمز (Memes)",
        "query": "funny memes laugh",
        "color": discord.Color.gold(),
        "emoji": "😂"
    },
    "cats": {
        "label": "قطط (Cats)",
        "query": "cute funny cats",
        "color": discord.Color.orange(),
        "emoji": "🐱"
    },
    "cyberpunk": {
        "label": "سايبربانك (Cyberpunk)",
        "query": "cyberpunk neon sci-fi",
        "color": discord.Color.teal(),
        "emoji": "🌆"
    }
}


async def fetch_tenor_gifs(query: str, limit: int = 15) -> list[dict]:
    """
    جلب الـ GIFs من Tenor API v2 باستخدام aiohttp بشكل غير متزامن.
    """
    url = "https://tenor.googleapis.com/v2/search"
    params = {
        "q": query,
        "key": TENOR_API_KEY,
        "client_key": TENOR_CLIENT_KEY,
        "limit": limit,
        "media_filter": "gif",
        "contentfilter": "medium"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    extracted = []
                    for item in results:
                        media = item.get("media_formats", {})
                        gif_obj = media.get("gif") or media.get("mediumgif")
                        if gif_obj and gif_obj.get("url"):
                            extracted.append({
                                "url": gif_obj["url"],
                                "title": item.get("content_description") or query
                            })
                    return extracted
                else:
                    print(f"[خطأ Tenor API] رمز الاستجابة: {resp.status}")
                    return []
    except Exception as e:
        print(f"[استثناء أثناء الاتصال بـ Tenor]: {e}")
        return []


class GifPaginationView(discord.ui.View):
    """
    أزرار تفاعلية للتنقل بين الـ GIFs (السابق / التالي / حذف الرسالة).
    """
    def __init__(self, gifs: list[dict], title: str, color: discord.Color, user: discord.User | discord.Member):
        super().__init__(timeout=180)  # تنتهي فعالية الأزرار بعد 3 دقائق
        self.gifs = gifs
        self.title = title
        self.color = color
        self.user = user
        self.index = 0
        self.update_buttons()

    def update_buttons(self):
        # تعطيل أو تمكين الأزرار حسب الموضع الحالي
        self.btn_prev.disabled = (self.index == 0)
        self.btn_next.disabled = (self.index >= len(self.gifs) - 1)

    def create_embed(self) -> discord.Embed:
        current_gif = self.gifs[self.index]
        embed = discord.Embed(
            title=f"✨ {self.title}",
            description=f"**الوصف:** {current_gif['title']}",
            color=self.color
        )
        embed.set_image(url=current_gif["url"])
        embed.set_footer(
            text=f"الصورة {self.index + 1} من {len(self.gifs)} • تم الطلب بواسطة {self.user.display_name}",
            icon_url=self.user.display_avatar.url
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # السماح فقط للشخص الذي طلب الأمر بالتفاعل مع الأزرار
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
        if self.index < len(self.gifs) - 1:
            self.index += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="🗑️ إغلاق", style=discord.ButtonStyle.danger, custom_id="btn_delete")
    async def btn_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    async def on_timeout(self):
        # تعطيل جميع الأزرار عند انتهاء الوقت
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True


class CategorySelect(discord.ui.Select):
    """
    قائمة منسدلة لاختيار الفئة.
    """
    def __init__(self, user: discord.User | discord.Member):
        options = [
            discord.SelectOption(
                label=data["label"],
                value=cat_key,
                emoji=data["emoji"]
            )
            for cat_key, data in CATEGORIES.items()
        ]
        super().__init__(placeholder="اختر فئة الصور/الـ GIF...", min_values=1, max_values=1, options=options)
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ هذه القائمة خاصة بصاحب الطلب فقط!", ephemeral=True)
            return

        selected_key = self.values[0]
        cat_data = CATEGORIES[selected_key]

        await interaction.response.defer()

        gifs = await fetch_tenor_gifs(cat_data["query"], limit=15)
        if not gifs:
            await interaction.followup.send("⚠️ لم يتم العثور على نتائج أو حدث خطأ في Tenor API.", ephemeral=True)
            return

        view = GifPaginationView(gifs=gifs, title=cat_data["label"], color=cat_data["color"], user=self.user)
        await interaction.edit_original_response(embed=view.create_embed(), view=view)


class CategorySelectView(discord.ui.View):
    def __init__(self, user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(user=user))


@bot.event
async def on_ready():
    # تشغيل خادم الويب لتلبية متطلبات Render Web Service
    try:
        await run_web_server()
    except Exception as e:
        print(f"⚠️ تنبيه خادم الويب: {e}")

    # تسجيل ومزامنة أوامر السلاش (Slash Commands)
    try:
        synced = await bot.tree.sync()
        print(f"✅ تم تسجيل {len(synced)} أمر سلاش بنجاح.")
    except Exception as e:
        print(f"❌ خطأ أثناء مزامنة الأوامر: {e}")
    print(f"🤖 البوت جاهز ويعمل باسم: {bot.user} (ID: {bot.user.id})")



# أمر سلاش لعرض قائمة الفئات
@bot.tree.command(name="categories", description="تصفح صور و GIFs بحسب الفئات المحددة مسبقاً")
async def slash_categories(interaction: discord.Interaction):
    if not TENOR_API_KEY:
        await interaction.response.send_message("⚠️ لم يتم ضبط مفتاح TENOR_API_KEY في ملف .env", ephemeral=True)
        return

    embed = discord.Embed(
        title="📂 اختر فئة لتصفح الـ GIFs",
        description="اختر إحدى الفئات من القائمة المنسدلة بالأسفل لعرض النتائج:",
        color=discord.Color.blurple()
    )
    view = CategorySelectView(user=interaction.user)
    await interaction.response.send_message(embed=embed, view=view)


# أمر سلاش للبحث المخصص عن أي GIF
@bot.tree.command(name="gif", description="ابحث عن أي GIF تريده بالاسم")
@app_commands.describe(query="الكلمة أو الموضوع الذي تريد البحث عنه")
async def slash_gif(interaction: discord.Interaction, query: str):
    if not TENOR_API_KEY:
        await interaction.response.send_message("⚠️ لم يتم ضبط مفتاح TENOR_API_KEY في ملف .env", ephemeral=True)
        return

    await interaction.response.defer()

    gifs = await fetch_tenor_gifs(query, limit=15)
    if not gifs:
        await interaction.followup.send(f"⚠️ لم يتم العثور على أي نتائج لكلمة: **{query}**", ephemeral=True)
        return

    view = GifPaginationView(
        gifs=gifs,
        title=f"نتائج البحث عن: {query}",
        color=discord.Color.blue(),
        user=interaction.user
    )
    await interaction.followup.send(embed=view.create_embed(), view=view)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ خطأ: يرجى وضع DISCORD_TOKEN في ملف .env قبل تشغيل البوت.")
    else:
        bot.run(DISCORD_TOKEN)
