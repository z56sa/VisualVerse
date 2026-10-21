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
 * دالة مجانية وسريعة جداً للترجمة المباشرة للعربية والإنجليزية دون الحاجة لأي مفتاح
 */
async function freeTranslateText(text, targetLang = 'ar') {
  if (!text || text.trim().length === 0) return text;
  try {
    const sl = targetLang === 'ar' ? 'auto' : 'ar';
    const tl = targetLang === 'ar' ? 'ar' : 'en';
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sl}&tl=${tl}&dt=t&q=${encodeURIComponent(text)}`;
    const res = await fetch(url);
    if (!res.ok) return text;
    const data = await res.json();
    if (data && data[0]) {
      const translated = data[0].map(segment => segment[0]).join('');
      return translated.trim() || text;
    }
  } catch (err) {
    console.warn('[Translate] Fallback error:', err.message);
  }
  return text;
}

/**
 * محاولة استدعاء Gemini مع تجربة الموديلات المتوفرة
 */
async function callGeminiWithFallback(apiKey, prompt) {
  const ai = getAIClient(apiKey);
  if (!ai) return null;

  // تجربة الموديلات بالترتيب الصحيح المتوافق مع v1beta و v1
  const modelsToTry = [
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-pro',
    'gemini-1.5-pro-latest'
  ];

  for (const modelName of modelsToTry) {
    try {
      const model = ai.getGenerativeModel({ model: modelName });
      const result = await model.generateContent(prompt);
      const text = result?.response?.text();
      if (text && text.trim().length > 0) {
        return text.trim();
      }
    } catch (err) {
      // نتجاهل الخطأ ونجرب الموديل التالي
    }
  }

  return null;
}

/**
 * تلخيص ومعالجة الخبر باللغتين العربية أو الإنجليزية
 */
export async function summarizeNewsItem(apiKey, title, content, lang = 'ar') {
  const isArabic = lang === 'ar';
  const cleanContent = (content || '').replace(/<[^>]*>/g, '').trim().slice(0, 400);

  // 1. محاولة الذكاء الاصطناعي أولاً
  if (apiKey && apiKey.trim().length > 0) {
    const prompt = isArabic
      ? `أنت محرر إخباري محترف لبوت FeedPulse على ديسكورد.
المطلوب:
1. صياغة عنوان عربي ملفت وجذاب لهذا الخبر.
2. تلخيص الخبر في 3 نقاط محددة ومفيدة باللغة العربية حصراً.

العنوان: ${title}
المحتوى: ${cleanContent || 'لا يوجد'}

الإخراج بهذا التنسيق تماماً:
العنوان: [العنوان بالعربية]
- [النقطة 1]
- [النقطة 2]
- [النقطة 3]`
      : `You are a professional news editor for the FeedPulse Discord bot.
Task:
1. Create a catchy English headline.
2. Summarize the news into 3 crisp bullet points in English.

Title: ${title}
Content: ${cleanContent || 'None'}

Strict Output format:
Title: [Catchy English title]
- [Point 1]
- [Point 2]
- [Point 3]`;

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

      if (summaryPoints.length > 0) {
        return {
          formattedTitle: formattedTitle || title,
          summaryPoints: summaryPoints.slice(0, 3)
        };
      }
    }
  }

  // 2. إذا لم يكن Gemini متاحاً أو فشل، نقوم بالترجمة التلقائية الفورية المجانية 100%!
  let finalTitle = title;
  let finalSnippet = cleanContent.slice(0, 220);

  if (isArabic) {
    finalTitle = await freeTranslateText(title, 'ar');
    if (finalSnippet) {
      finalSnippet = await freeTranslateText(finalSnippet, 'ar');
    }
  }

  return {
    formattedTitle: finalTitle,
    summaryPoints: [
      finalSnippet ? finalSnippet + (cleanContent.length > 220 ? '...' : '') : (isArabic ? 'اضغط على الرابط بالأسفل لقراءة تفاصيل هذا الخبر.' : 'Click below to read full details.'),
      isArabic
        ? '🔗 اضغط على زر المصدر أدناه لقراءة التفاصيل الكاملة.'
        : '🔗 Click the source button below to read full details.'
    ]
  };
}

/**
 * توليد الحصاد الإخباري اليومي
 */
export async function generateDailyRecap(apiKey, newsItems) {
  return generateDailyRecapWithLang(apiKey, newsItems, 'ar');
}

export async function generateDailyRecapWithLang(apiKey, newsItems, lang = 'ar') {
  const isArabic = lang === 'ar';

  if (!Array.isArray(newsItems) || newsItems.length === 0) {
    return isArabic ? '⚠️ لا توجد أخبار كافية لتوليد الحصاد اليومي.' : '⚠️ No news items available for daily recap.';
  }

  const newsListText = newsItems
    .map((n, i) => `${i + 1}. ${n.title} [${n.source}]`)
    .join('\n');

  // 1. محاولة Gemini
  if (apiKey && apiKey.trim().length > 0) {
    const prompt = isArabic
      ? `أنت محرر إخباري تنفيذي.
إليك قائمة بأبرز أخبار اليوم:
${newsListText}

المطلوب:
- ترجم وصغ نشرة موجزة بعنوان "⚡ حصاد FeedPulse الإخباري اليومي" باللغة العربية الفصحى حصراً.
- لخص أهم الأخبار في 5 نقاط واضحة وممتعة مع إيموجي مناسب لكل نقطة.`
      : `You are an executive news editor.
Here is today's top stories:
${newsListText}

Task:
- Write a daily brief titled "⚡ FeedPulse Daily Highlights" in English.
- Summarize the top stories in 5 informative bullet points with emojis.`;

    const aiSummary = await callGeminiWithFallback(apiKey, prompt);
    if (aiSummary) return aiSummary;
  }

  // 2. الترجمة التلقائية الفورية المجانية والمضمونة 100% لكل الأخبار!
  const translatedItems = [];
  for (const item of newsItems.slice(0, 6)) {
    const translatedTitle = isArabic ? await freeTranslateText(item.title, 'ar') : item.title;
    translatedItems.push(`🔹 **${translatedTitle}** *(${item.source})*`);
  }

  const header = isArabic
    ? '📊 **⚡ حصاد FeedPulse الإخباري اليومي:**\n'
    : '📊 **⚡ FeedPulse Daily News Highlights:**\n';

  return header + translatedItems.join('\n');
}
