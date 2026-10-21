import { GoogleGenerativeAI } from '@google/generative-ai';

let genAI = null;

function getAIClient(apiKey) {
  if (!apiKey) return null;
  if (!genAI) {
    genAI = new GoogleGenerativeAI(apiKey);
  }
  return genAI;
}

/**
 * دالة استدعاء الموديل مع التبديل التلقائي إذا كان الموديل الأول مشغولاً
 */
async function callGeminiWithFallback(apiKey, prompt) {
  const ai = getAIClient(apiKey);
  if (!ai) return null;

  const modelsToTry = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro'];

  for (const modelName of modelsToTry) {
    try {
      const model = ai.getGenerativeModel({ model: modelName });
      const result = await model.generateContent(prompt);
      const text = result?.response?.text();
      if (text && text.trim().length > 0) {
        return text.trim();
      }
    } catch (err) {
      console.warn(`[Gemini] Model ${modelName} error:`, err.message);
    }
  }
  return null;
}

/**
 * تلخيص ومعالجة الخبر باللغتين العربية أو الإنجليزية
 * @param {string} apiKey 
 * @param {string} title 
 * @param {string} content 
 * @param {'ar' | 'en'} lang 
 * @returns {Promise<{ formattedTitle: string, summaryPoints: string[] }>}
 */
export async function summarizeNewsItem(apiKey, title, content, lang = 'ar') {
  const isArabic = lang === 'ar';
  const cleanSnippet = (content || title || '').replace(/<[^>]*>/g, '').trim();

  if (apiKey && apiKey.trim().length > 0) {
    const prompt = isArabic
      ? `
أنت محرر إخباري محترف مسؤول عن بوت FeedPulse في ديسكورد.
مهمتك: قراءة الخبر التالي، ثم كتابة عنوان عربي ملفت وجذاب، وتلخيص الخبر في 3 نقاط محددة وواضحة جداً باللغة العربية حصراً.

عنوان الخبر: ${title}
نص الخبر: ${cleanSnippet || 'لا يوجد نص إضافي'}

المطلوب إخراجه بهذا التنسيق الصارم دون أي مقدمات:
العنوان: [العنوان باللغة العربية]
- [النقطة الأولى بالعربية]
- [النقطة الثانية بالعربية]
- [النقطة الثالثة بالعربية]
`
      : `
You are a professional news editor for the FeedPulse Discord bot.
Your task: Read the following news item, craft an engaging English headline, and summarize the key facts in 3 crisp bullet points in English.

News Title: ${title}
News Content: ${cleanSnippet || 'No additional content'}

Output strictly in this format without introductory banter:
Title: [Catchy concise English title]
- [Key point 1]
- [Key point 2]
- [Key point 3]
`;

    const responseText = await callGeminiWithFallback(apiKey, prompt);

    if (responseText) {
      const lines = responseText.split('\n').map(l => l.trim()).filter(Boolean);
      let formattedTitle = title;
      const summaryPoints = [];

      for (const line of lines) {
        if (line.startsWith('العنوان:') || line.startsWith('Title:')) {
          formattedTitle = line.replace(/^(العنوان:|Title:)\s*/, '').trim();
        } else if (line.startsWith('-') || line.startsWith('•') || line.startsWith('*')) {
          summaryPoints.push(line.replace(/^[-•*]\s*/, '').trim());
        }
      }

      if (summaryPoints.length === 0) {
        summaryPoints.push(responseText.slice(0, 300));
      }

      return {
        formattedTitle: formattedTitle || title,
        summaryPoints: summaryPoints.slice(0, 3)
      };
    }
  }

  // في حال لم يعمل الـ AI
  return {
    formattedTitle: title,
    summaryPoints: [
      cleanSnippet.slice(0, 160) + (cleanSnippet.length > 160 ? '...' : ''),
      isArabic ? 'اضغط على زر المصدر أدناه لقراءة التفاصيل الكاملة للخبر.' : 'Click below to read the full report.'
    ]
  };
}

/**
 * توليد ملخص إخباري يومي شامل (عربي أو إنجليزي)
 * @param {string} apiKey 
 * @param {Array<{ title: string, source: string }>} newsItems 
 * @param {'ar' | 'en'} lang 
 * @returns {Promise<string>}
 */
export async function generateDailyRecap(apiKey, newsItems) {
  return generateDailyRecapWithLang(apiKey, newsItems, 'ar');
}

export async function generateDailyRecapWithLang(apiKey, newsItems, lang = 'ar') {
  const isArabic = lang === 'ar';

  if (!Array.isArray(newsItems) || newsItems.length === 0) {
    return isArabic ? '⚠️ لا توجد أخبار كافية.' : '⚠️ No news items available.';
  }

  const newsListText = newsItems.map((n, i) => `${i + 1}. ${n.title} [${n.source}]`).join('\n');

  if (apiKey && apiKey.trim().length > 0) {
    const prompt = isArabic
      ? `
أنت محرر إخباري محترف. لديك قائمة بأبرز الأخبار اليومية العالمية:
${newsListText}

المطلوب:
صياغة نشرة موجزة بعنوان "⚡ حصاد اليوم الإخباري من FeedPulse" باللغة العربية حصراً.
لخص أهم 4 إلى 5 أحداث ومجريات رئيسية في نقاط واضحة وممتعة للقراءة باللغة العربية.
`
      : `
You are an executive news editor. Here is today's top global news list:
${newsListText}

Task:
Craft a concise, professional daily news brief titled "⚡ FeedPulse Daily Highlights" in English.
Summarize the 4 to 5 biggest trends and stories in informative, engaging bullet points.
`;

    const aiSummary = await callGeminiWithFallback(apiKey, prompt);
    if (aiSummary) {
      return aiSummary;
    }
  }

  // Fallback إذا فشل الاتصال بالذكاء الاصطناعي
  return isArabic
    ? '📊 **نشرة FeedPulse الإخبارية اليومية:**\n' + newsItems.map((n, i) => `🔹 **${n.title}** (${n.source})`).join('\n')
    : '📊 **FeedPulse Daily News Brief:**\n' + newsItems.map((n, i) => `🔹 **${n.title}** (${n.source})`).join('\n');
}
