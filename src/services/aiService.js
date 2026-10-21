import { GoogleGenerativeAI } from '@google/generative-ai';

let genAI = null;

function getAIClient(apiKey) {
  if (!apiKey || apiKey.trim().length === 0) return null;
  if (!genAI) {
    genAI = new GoogleGenerativeAI(apiKey.trim());
  }
  return genAI;
}

/**
 * استدعاء Gemini مع Fallback تلقائي بين الموديلات
 */
async function callGeminiWithFallback(apiKey, prompt) {
  const ai = getAIClient(apiKey);
  if (!ai) {
    console.warn('[Gemini] No API key provided.');
    return null;
  }

  const modelsToTry = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro'];

  for (const modelName of modelsToTry) {
    try {
      console.log(`[Gemini] Trying model: ${modelName}`);
      const model = ai.getGenerativeModel({ model: modelName });
      const result = await model.generateContent(prompt);
      const text = result?.response?.text();
      if (text && text.trim().length > 0) {
        console.log(`[Gemini] ✅ Success with model: ${modelName}`);
        return text.trim();
      }
    } catch (err) {
      console.warn(`[Gemini] Model ${modelName} failed:`, err.message);
    }
  }

  console.error('[Gemini] ❌ All models failed.');
  return null;
}

/**
 * تلخيص خبر واحد وترجمته (عربي أو إنجليزي)
 * @param {string} apiKey
 * @param {string} title
 * @param {string} content
 * @param {'ar' | 'en'} lang
 */
export async function summarizeNewsItem(apiKey, title, content, lang = 'ar') {
  const isArabic = lang === 'ar';
  const cleanContent = (content || '').replace(/<[^>]*>/g, '').trim().slice(0, 400);

  if (apiKey && apiKey.trim().length > 0) {
    const prompt = isArabic
      ? `أنت محرر إخباري محترف لبوت FeedPulse على ديسكورد.
المطلوب: اقرأ الخبر التالي ثم:
1. اكتب عنواناً عربياً ملفتاً وجذاباً.
2. لخص الخبر في 3 نقاط واضحة ومفيدة باللغة العربية الفصحى حصراً.

عنوان الخبر: ${title}
محتوى الخبر: ${cleanContent || 'لا يوجد محتوى إضافي'}

الإخراج المطلوب بهذا التنسيق تماماً بدون أي مقدمات:
العنوان: [العنوان بالعربية]
- [النقطة الأولى]
- [النقطة الثانية]
- [النقطة الثالثة]`
      : `You are a professional news editor for the FeedPulse Discord bot.
Task: Read the news item below and:
1. Write a catchy, concise English headline.
2. Summarize the key facts in 3 clear bullet points in English.

News Title: ${title}
News Content: ${cleanContent || 'No additional content available'}

Output strictly in this format with no intro:
Title: [Catchy English title]
- [Key point 1]
- [Key point 2]
- [Key point 3]`;

    const responseText = await callGeminiWithFallback(apiKey, prompt);

    if (responseText) {
      const lines = responseText.split('\n').map(l => l.trim()).filter(Boolean);
      let formattedTitle = title;
      const summaryPoints = [];

      for (const line of lines) {
        if (line.startsWith('العنوان:') || line.startsWith('Title:')) {
          formattedTitle = line.replace(/^(العنوان:|Title:)\s*/, '').trim();
        } else if (line.startsWith('-') || line.startsWith('•') || line.startsWith('*')) {
          const point = line.replace(/^[-•*]\s*/, '').trim();
          if (point.length > 0) summaryPoints.push(point);
        }
      }

      if (summaryPoints.length === 0 && responseText.length > 0) {
        summaryPoints.push(responseText.slice(0, 250));
      }

      return {
        formattedTitle: formattedTitle || title,
        summaryPoints: summaryPoints.slice(0, 3)
      };
    }
  }

  // Fallback ذكي بدون AI
  const snippet = cleanContent.slice(0, 160);
  return {
    formattedTitle: title,
    summaryPoints: [
      snippet ? snippet + (cleanContent.length > 160 ? '...' : '') : (isArabic ? 'لا يوجد ملخص متاح لهذا الخبر.' : 'No summary available for this news item.'),
      isArabic
        ? '🔗 اضغط على زر المصدر أدناه لقراءة التفاصيل الكاملة.'
        : '🔗 Click the source button below to read the full story.'
    ]
  };
}

/**
 * توليد حصاد يومي (يستخدم generateDailyRecapWithLang داخلياً)
 */
export async function generateDailyRecap(apiKey, newsItems) {
  return generateDailyRecapWithLang(apiKey, newsItems, 'ar');
}

/**
 * توليد ملخص يومي شامل باللغة المحددة
 * @param {string} apiKey
 * @param {Array<{ title: string, source: string }>} newsItems
 * @param {'ar' | 'en'} lang
 */
export async function generateDailyRecapWithLang(apiKey, newsItems, lang = 'ar') {
  const isArabic = lang === 'ar';

  if (!Array.isArray(newsItems) || newsItems.length === 0) {
    return isArabic ? '⚠️ لا توجد أخبار كافية لتوليد الحصاد اليومي.' : '⚠️ No news items available for the daily recap.';
  }

  const newsListText = newsItems
    .map((n, i) => `${i + 1}. ${n.title} [${n.source}]`)
    .join('\n');

  if (apiKey && apiKey.trim().length > 0) {
    const prompt = isArabic
      ? `أنت محرر إخباري تنفيذي محترف.
لديك قائمة بأبرز أخبار اليوم:
${newsListText}

المطلوب:
- ترجم جميع العناوين للعربية إن كانت بالإنجليزية.
- اكتب نشرة إخبارية احترافية بعنوان "⚡ حصاد FeedPulse الإخباري اليومي" باللغة العربية الفصحى حصراً.
- لخص أهم 5 أحداث في نقاط واضحة ومشوقة باللغة العربية.
- استخدم إيموجيات مناسبة لكل نقطة.`
      : `You are a professional executive news editor.
Here is today's top news list:
${newsListText}

Task:
- Write a professional daily news brief titled "⚡ FeedPulse Daily News Highlights" in English.
- Summarize the 5 biggest stories in clear, engaging bullet points.
- Use appropriate emojis for each point.`;

    const aiSummary = await callGeminiWithFallback(apiKey, prompt);
    if (aiSummary) return aiSummary;
  }

  // Fallback جميل بدون AI
  const header = isArabic
    ? '📊 **⚡ حصاد FeedPulse الإخباري اليومي:**\n'
    : '📊 **⚡ FeedPulse Daily News Highlights:**\n';

  return header + newsItems.map(n => `🔹 **${n.title}** *(${n.source})*`).join('\n');
}
