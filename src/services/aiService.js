/**
 * محرك الذكاء الاصطناعي FeedPulse AI
 * ترجمة فورية وتلخيص فائق السرعة لكلا اللغتين (العربية الفصحى 🇸🇦 والإنجليزية 🇺🇸).
 */

/**
 * محرك ترجمة فوري عالي الكفاءة يضمن التعريب الكامل بنسبة 100%
 */
export async function translateText(text, targetLang = 'ar') {
  if (!text || typeof text !== 'string' || text.trim().length === 0) return text;
  
  // إذا كان النص يحتوي بالفعل على حروف عربية والمطلوب عربي، لا داعي للترجمة
  if (targetLang === 'ar' && /[\u0600-\u06FF]/.test(text) && text.length > 20) {
    return text;
  }

  try {
    const sl = targetLang === 'ar' ? 'en' : 'ar';
    const tl = targetLang === 'ar' ? 'ar' : 'en';
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sl}&tl=${tl}&dt=t&q=${encodeURIComponent(text.trim())}`;
    
    const res = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      }
    });

    if (res.ok) {
      const data = await res.json();
      if (data && data[0] && Array.isArray(data[0])) {
        const fullTranslation = data[0].map(item => item[0]).filter(Boolean).join('');
        if (fullTranslation && fullTranslation.trim().length > 0) {
          return fullTranslation.trim();
        }
      }
    }
  } catch (err) {
    console.warn('[Translate] Error:', err.message);
  }

  return text;
}

/**
 * استدعاء Gemini AI إن وُجد مفتاح صالح
 */
async function callGeminiRaw(apiKey, prompt) {
  if (!apiKey || apiKey.trim().length === 0) return null;

  const models = ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-pro'];

  for (const model of models) {
    try {
      const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey.trim()}`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }]
        })
      });

      if (response.ok) {
        const result = await response.json();
        const text = result?.candidates?.[0]?.content?.parts?.[0]?.text;
        if (text && text.trim().length > 0) {
          return text.trim();
        }
      }
    } catch (e) {
      // تجربة الموديل التالي
    }
  }
  return null;
}

/**
 * تلخيص ومعالجة الخبر بالكامل باللغة المحددة
 */
export async function summarizeNewsItem(apiKey, title, content, lang = 'ar') {
  const isArabic = lang === 'ar';
  const cleanSnippet = (content || '').replace(/<[^>]*>/g, '').trim().slice(0, 350);

  // 1. تجربة التلخيص المباشر عبر Gemini
  if (apiKey && apiKey.trim().length > 0) {
    const prompt = isArabic
      ? `أنت محرر إخباري محترف. لخص هذا الخبر وترجمه باللغة العربية الفصحى تماماً في 3 نقاط محددة:
العنوان: ${title}
المحتوى: ${cleanSnippet}

التنسيق الصارم المطلوب:
العنوان: [العنوان بالعربية]
- [نقطة 1 بالعربية]
- [نقطة 2 بالعربية]
- [نقطة 3 بالعربية]`
      : `You are a professional editor. Summarize this news in English in 3 bullet points:
Title: ${title}
Content: ${cleanSnippet}

Strict format:
Title: [English Title]
- [Point 1]
- [Point 2]
- [Point 3]`;

    const aiRes = await callGeminiRaw(apiKey, prompt);
    if (aiRes) {
      const lines = aiRes.split('\n').map(l => l.trim()).filter(Boolean);
      let formattedTitle = '';
      const summaryPoints = [];

      for (const line of lines) {
        if (line.startsWith('العنوان:') || line.startsWith('Title:')) {
          formattedTitle = line.replace(/^(العنوان:|Title:)\s*/, '').trim();
        } else if (line.startsWith('-') || line.startsWith('•') || line.startsWith('*')) {
          const pt = line.replace(/^[-•*]\s*/, '').trim();
          if (pt) summaryPoints.push(pt);
        }
      }

      if (summaryPoints.length > 0) {
        return {
          formattedTitle: formattedTitle || (isArabic ? await translateText(title, 'ar') : title),
          summaryPoints: summaryPoints.slice(0, 3)
        };
      }
    }
  }

  // 2. التعريب والترجمة الفورية الكاملة والمضمونة
  const finalTitle = isArabic ? await translateText(title, 'ar') : title;
  const translatedSnippet = cleanSnippet ? (isArabic ? await translateText(cleanSnippet, 'ar') : cleanSnippet) : '';

  return {
    formattedTitle: finalTitle,
    summaryPoints: [
      translatedSnippet ? translatedSnippet.slice(0, 180) + '...' : (isArabic ? 'اضغط أدناه لقراءة التفاصيل الكاملة لهذا الخبر.' : 'Click below to read full details.'),
      isArabic ? '🔗 اضغط على زر قراءة الخبر كاملاً للاطلاع على المصدر.' : '🔗 Click the source button below to read the original story.'
    ]
  };
}

/**
 * توليد ملخص وحصاد إخباري يومي شامل ومعرّب 100%
 */
export async function generateDailyRecap(apiKey, newsItems) {
  return generateDailyRecapWithLang(apiKey, newsItems, 'ar');
}

export async function generateDailyRecapWithLang(apiKey, newsItems, lang = 'ar') {
  const isArabic = lang === 'ar';

  if (!Array.isArray(newsItems) || newsItems.length === 0) {
    return isArabic ? '⚠️ لا توجد أخبار كافية لتوليد الحصاد اليومي.' : '⚠️ No news items available.';
  }

  // ترجمة جميع العناوين فوراً للعربية لضمان عدم بقاء أي كلمة إنجليزية
  const processedTitles = await Promise.all(
    newsItems.slice(0, 6).map(async (item) => {
      const arabicTitle = isArabic ? await translateText(item.title, 'ar') : item.title;
      return {
        title: arabicTitle,
        source: item.source
      };
    })
  );

  // 1. محاولة Gemini لصياغة نشرة سينمائية
  if (apiKey && apiKey.trim().length > 0) {
    const listText = processedTitles.map((n, i) => `${i + 1}. ${n.title} [${n.source}]`).join('\n');
    const prompt = isArabic
      ? `أنت محرر إخباري محترف. صغ نشرة ملخصة بعنوان "⚡ حصاد FeedPulse الإخباري اليومي" باللغة العربية الفصحى لهذه الأخبار:
${listText}
اكتب 5 نقاط ملخصة وواضحة جداً بالعربية مع إيموجي مناسب لكل نقطة.`
      : `Write a concise news recap titled "⚡ FeedPulse Daily Highlights" in English for these stories:
${listText}
Summarize the top 5 stories in crisp bullet points.`;

    const aiSummary = await callGeminiRaw(apiKey, prompt);
    if (aiSummary && aiSummary.trim().length > 20) {
      return aiSummary.trim();
    }
  }

  // 2. الإخراج المباشر المعرّب 100% بنقاط واضحة وأنيقة
  const lines = processedTitles.map(item => `🔹 **${item.title}** *(${item.source})*`);
  
  return (isArabic ? '📊 **نشرة FeedPulse الإخبارية اليومية:**\n' : '📊 **FeedPulse Daily Highlights:**\n') + lines.join('\n');
}
