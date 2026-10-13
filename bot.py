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
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
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
        "query": "gaming video games wallpaper gif",
        "color": discord.Color.purple(),
        "emoji": "🎮"
    },
    "anime": {
        "label": "أنمي (Anime)",
        "query": "anime aesthetic gif",
        "color": discord.Color.magenta(),
        "emoji": "🌸"
    },
    "nature": {
        "label": "طبيعة (Nature)",
        "query": "nature landscape photography gif",
        "color": discord.Color.green(),
        "emoji": "🌿"
    },
    "memes": {
        "label": "ميمز (Memes)",
        "query": "funny memes gif",
        "color": discord.Color.gold(),
        "emoji": "😂"
    },
    "cats": {
        "label": "قطط (Cats)",
        "query": "cute funny cats gif",
        "color": discord.Color.orange(),
        "emoji": "🐱"
    },
    "cyberpunk": {
        "label": "سايبربانك (Cyberpunk)",
        "query": "cyberpunk neon aesthetic gif",
        "color": discord.Color.teal(),
        "emoji": "🌆"
    }
}


async def fetch_google_images(query: str, search_type: str = "animated", limit: int = 10) -> list[dict]:
    """
    جلب الصور / الـ GIFs عبر Google Custom Search Engine (CSE) API.
    search_type: 'animated' لجلب الـ GIFs المتحركة، أو 'image' لجلب صور عامة.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "searchType": "image",
        "num": min(limit, 10),
        "safe": "active"
    }

    if search_type == "animated":
        params["fileType"] = "gif"
        params["hq"] = "animated"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    extracted = []
                    for item in items:
                        img_url = item.get("link")
                        if img_url:
                            extracted.append({
                                "url": img_url,
                                "title": item.get("title", query)
                            })
                    return extracted
                else:
                    err_body = await resp.text()
                    print(f"[خطأ Google API] رمز: {resp.status} - {err_body}")
                    return []
    except Exception as e:
        print(f"[استثناء أثناء الاتصال بـ Google API]: {e}")
        return []


class ImagePaginationView(discord.ui.View):
    """
    أزرار تفاعلية للتنقل بين الصور والـ GIFs (السابق / التالي / حذف الرسالة).
    """
    def __init__(self, items: list[dict], title: str, color: discord.Color, user: discord.User | discord.Member):
        super().__init__(timeout=180)
        self.items = items
        self.title = title
        self.color = color
        self.user = user
        self.index = 0
        self.update_buttons()

    def update_buttons(self):
        self.btn_prev.disabled = (self.index == 0)
        self.btn_next.disabled = (self.index >= len(self.items) - 1)

    def create_embed(self) -> discord.Embed:
        current_item = self.items[self.index]
        embed = discord.Embed(
            title=f"✨ {self.title}",
            description=f"**العنوان:** {current_item['title']}",
            color=self.color
        )
        embed.set_image(url=current_item["url"])
        embed.set_footer(
            text=f"النتيجة {self.index + 1} من {len(self.items)} • تم الطلب بواسطة {self.user.display_name}",
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

        items = await fetch_google_images(cat_data["query"], search_type="animated", limit=10)
        if not items:
            await interaction.followup.send("⚠️ لم يتم العثور على نتائج أو حدث خطأ أثناء الاتصال بـ Google API.", ephemeral=True)
            return

        view = ImagePaginationView(items=items, title=cat_data["label"], color=cat_data["color"], user=self.user)
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
@bot.tree.command(name="categories", description="تصفح صور و GIFs بحسب الفئات المحددة مسبقاً عبر Google")
async def slash_categories(interaction: discord.Interaction):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        await interaction.response.send_message("⚠️ لم يتم ضبط GOOGLE_API_KEY أو GOOGLE_CSE_ID في متغيرات البيئة.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📂 اختر فئة لتصفح الصور والـ GIFs",
        description="اختر إحدى الفئات من القائمة المنسدلة بالأسفل لعرض النتائج عبر Google:",
        color=discord.Color.blurple()
    )
    view = CategorySelectView(user=interaction.user)
    await interaction.response.send_message(embed=embed, view=view)


# أمر سلاش للبحث المخصص عن أي GIF أو صورة
@bot.tree.command(name="image", description="ابحث عن صور أو متحركات عبر Google Custom Search")
@app_commands.describe(
    query="الكلمة أو الموضوع الذي تريد البحث عنه",
    gif_only="هل تبحث عن صور متحركة GIF فقط؟ (نعم / لا)"
)
async def slash_image(interaction: discord.Interaction, query: str, gif_only: bool = True):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        await interaction.response.send_message("⚠️ لم يتم ضبط GOOGLE_API_KEY أو GOOGLE_CSE_ID في متغيرات البيئة.", ephemeral=True)
        return

    await interaction.response.defer()

    search_type = "animated" if gif_only else "image"
    items = await fetch_google_images(query, search_type=search_type, limit=10)
    if not items:
        await interaction.followup.send(f"⚠️ لم يتم العثور على أي نتائج لكلمة: **{query}**", ephemeral=True)
        return

    view = ImagePaginationView(
        items=items,
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
