/**
 * محرك الذكاء الاصطناعي FeedPulse AI
 * يدعم كلا اللغتين (العربية 🇸🇦 والإنجليزية 🇺🇸) بشكل كامل ومباشر.
 * يتصل بـ Google Gemini API مع اكتشاف تلقائي للموديلات الفعالة والترجمة الفورية المزدوجة.
 */

let cachedWorkingModel = null;

/**
 * جلب قائمة الموديلات الصالحة تلقائياً لمفتاح الـ API الممرر
 */
async function discoverWorkingModel(apiKey) {
  if (cachedWorkingModel) return cachedWorkingModel;
  if (!apiKey || apiKey.trim().length === 0) return null;

  try {
    const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey.trim()}`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.models)) {
        // البحث عن أفضل موديل يدعم generateContent
        const validModel = data.models.find(m => 
          m.supportedGenerationMethods?.includes('generateContent') &&
          (m.name.includes('flash') || m.name.includes('gemini'))
        );
        if (validModel) {
          // إزالة بادئة "models/" إذا وُجدت
          cachedWorkingModel = validModel.name.replace(/^models\//, '');
          console.log(`[FeedPulse AI] ✅ Discovered active Gemini model: ${cachedWorkingModel}`);
          return cachedWorkingModel;
        }
      }
    }
  } catch (err) {
    console.warn('[FeedPulse AI] Model auto-discovery warning:', err.message);
  }

  // افتراضيات حديثة متوافقة
  return 'gemini-1.5-flash';
}

/**
 * إرسال طلب توليد محتوى مباشر للـ Gemini REST API لضمان عدم وجود أخطاء في الـ SDK
 */
async function requestGemini(apiKey, prompt) {
  if (!apiKey || apiKey.trim().length === 0) return null;

  const model = await discoverWorkingModel(apiKey);
  const modelsToTry = [model, 'gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-pro'].filter(Boolean);
  const uniqueModels = [...new Set(modelsToTry)];

  for (const m of uniqueModels) {
    try {
      const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${apiKey.trim()}`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [
            {
              parts: [{ text: prompt }]
            }
          ]
        })
      });

      if (response.ok) {
        const result = await response.json();
        const text = result?.candidates?.[0]?.content?.parts?.[0]?.text;
        if (text && text.trim().length > 0) {
          cachedWorkingModel = m;
          return text.trim();
        }
      } else {
        const errJson = await response.json().catch(() => ({}));
        console.warn(`[FeedPulse AI] Model ${m} returned HTTP ${response.status}:`, errJson?.error?.message || response.statusText);
      }
    } catch (e) {
      console.warn(`[FeedPulse AI] Model ${m} network error:`, e.message);
    }
  }

  return null;
}

/**
 * محرك ترجمة مدمج وسريع لضمان ترجمة النصوص للغتين حتى في حال انقطاع الذكاء الاصطناعي
 */
async function translateText(text, targetLang = 'ar') {
  if (!text || text.trim().length === 0) return text;
  try {
    const sl = targetLang === 'ar' ? 'auto' : 'ar';
    const tl = targetLang === 'ar' ? 'ar' : 'en';
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sl}&tl=${tl}&dt=t&q=${encodeURIComponent(text)}`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      if (data && data[0]) {
        return data[0].map(s => s[0]).join('').trim() || text;
      }
    }
  } catch (err) {
    // ignore
  }
  return text;
}

/**
 * تلخيص ومعالجة الخبر بالذكاء الاصطناعي باللغتين (عربي / إنجليزي)
 * @param {string} apiKey 
 * @param {string} title 
 * @param {string} content 
 * @param {'ar' | 'en'} lang 
 */
export async function summarizeNewsItem(apiKey, title, content, lang = 'ar') {
  const isArabic = lang === 'ar';
  const cleanContent = (content || '').replace(/<[^>]*>/g, '').trim().slice(0, 500);

  // 1. محاولة الذكاء الاصطناعي AI
  const prompt = isArabic
    ? `أنت محرر إخباري محترف لبوت FeedPulse.
المهمة:
1. قم بترجمة وصياغة عنوان عربي شيق وجذاب لهذا الخبر.
2. لخص الخبر في 3 نقاط ذكية وموجزة باللغة العربية الفصحى فقط.

عنوان الخبر: ${title}
تفاصيل الخبر: ${cleanContent || 'لا يوجد'}

التنسيق المطلوب بالضبط:
العنوان: [العنوان بالعربية]
- [النقطة 1]
- [النقطة 2]
- [النقطة 3]`
    : `You are a professional news editor for the FeedPulse bot.
Task:
1. Craft an engaging English headline for this news story.
2. Summarize the story into 3 concise and impactful bullet points in English.

News Title: ${title}
Details: ${cleanContent || 'None'}

Strict Output Format:
Title: [Catchy English Title]
- [Point 1]
- [Point 2]
- [Point 3]`;

  const aiResponse = await requestGemini(apiKey, prompt);

  if (aiResponse) {
    const lines = aiResponse.split('\n').map(l => l.trim()).filter(Boolean);
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

  // 2. خطة الأمان الفورية (ترجمة تلقائية للغة المختارة)
  let finalTitle = title;
  let finalSnippet = cleanContent.slice(0, 220);

  if (isArabic) {
    finalTitle = await translateText(title, 'ar');
    if (finalSnippet) finalSnippet = await translateText(finalSnippet, 'ar');
  } else {
    // إذا كان الإنجليزي هو المطلوب والخبر بلغة أخرى
    finalTitle = await translateText(title, 'en');
    if (finalSnippet) finalSnippet = await translateText(finalSnippet, 'en');
  }

  return {
    formattedTitle: finalTitle,
    summaryPoints: [
      finalSnippet ? finalSnippet + (cleanContent.length > 220 ? '...' : '') : (isArabic ? 'اضغط أدناه لقراءة التفاصيل الكاملة.' : 'Click below to read full details.'),
      isArabic ? '🔗 اضغط على زر المصدر أدناه لقراءة التفاصيل الكاملة.' : '🔗 Click the source button below to read the full report.'
    ]
  };
}

/**
 * توليد ملخص وحصاد إخباري يومي شامل بالذكاء الاصطناعي لكلا اللغتين
 */
export async function generateDailyRecap(apiKey, newsItems) {
  return generateDailyRecapWithLang(apiKey, newsItems, 'ar');
}

export async function generateDailyRecapWithLang(apiKey, newsItems, lang = 'ar') {
  const isArabic = lang === 'ar';

  if (!Array.isArray(newsItems) || newsItems.length === 0) {
    return isArabic ? '⚠️ لا توجد أخبار كافية لتوليد الحصاد اليومي.' : '⚠️ Not enough news articles to generate recap.';
  }

  const newsList = newsItems.map((n, i) => `${i + 1}. ${n.title} [${n.source}]`).join('\n');

  // 1. محاولة الذكاء الاصطناعي
  const prompt = isArabic
    ? `أنت محرر إخباري تنفيذي. لديك هذه القائمة من الأخبار:
${newsList}

المطلوب:
- صغ ملخصاً إخبارياً مشوقاً بعنوان "⚡ حصاد FeedPulse الإخباري اليومي" باللغة العربية حصراً.
- لخص أهم 5 أحداث في نقاط موجزة ومفيدة باللغة العربية مع إيموجي لكل نقطة.`
    : `You are an executive news editor. Here is today's news list:
${newsList}

Task:
- Write a daily news brief titled "⚡ FeedPulse Daily Highlights" in English.
- Summarize the top 5 stories in concise bullet points with suitable emojis.`;

  const aiText = await requestGemini(apiKey, prompt);
  if (aiText) return aiText;

  // 2. خطة أمان الترجمة
  const formattedItems = [];
  for (const item of newsItems.slice(0, 6)) {
    const translatedTitle = isArabic ? await translateText(item.title, 'ar') : await translateText(item.title, 'en');
    formattedItems.push(`🔹 **${translatedTitle}** *(${item.source})*`);
  }

  const header = isArabic
    ? '📊 **⚡ حصاد FeedPulse الإخباري اليومي:**\n'
    : '📊 **⚡ FeedPulse Daily News Highlights:**\n';

  return header + formattedItems.join('\n');
}
