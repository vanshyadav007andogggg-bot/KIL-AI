# KIL AI — शुरुआती ऑनलाइन प्रोजेक्ट

इस पैकेज में FastAPI backend और मोबाइल-अनुकूल चैट वेबसाइट है। वेबसाइट में:
- हिंदी Detective-style KIL prompt
- Groq Chat Completions API
- `wiki: विषय` कमांड
- ब्राउज़र में उपलब्ध होने पर आवाज़ से बोलकर इनपुट
- ब्राउज़र के Text-to-Speech से जवाब सुनना

## सुरक्षा — पहले यह करें
आपकी पिछली स्क्रिप्ट में API key खुली हुई थी। उसे Groq Dashboard से revoke करें और नई key बनाएं।
नई key किसी चैट, स्क्रीनशॉट, GitHub repository या APK में न डालें। उसे hosting dashboard में
`GROQ_API_KEY` नाम के secret environment variable के रूप में सेट करें।

## ऑनलाइन चलाने का तरीका
1. इस ZIP को extract करें।
2. पूरा `KIL_AI_Project` folder अपने GitHub repository में upload करें।
3. Render पर New > Web Service चुनें और उस repository को connect करें।
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Render के Environment में `GROQ_API_KEY` नाम और नई Groq key value सेट करें।
7. Deploy पूरा होने पर Render आपको `https://....onrender.com` URL देगा।

API health check: `https://YOUR-SERVICE.onrender.com/api/health`
Chat endpoint: `POST https://YOUR-SERVICE.onrender.com/api/chat`

## लोकल टेस्ट
Python 3.10+ के साथ:
```bash
pip install -r requirements.txt
# Linux/macOS:
export GROQ_API_KEY="अपनी-नई-key"
# Windows PowerShell:
# $env:GROQ_API_KEY="अपनी-नई-key"
uvicorn main:app --reload
```
फिर `http://127.0.0.1:8000` खोलें।

## APK के बारे में
यह पहला पैकेज responsive web app है, जो Android Chrome पर भी चलेगा। इसे पहले ऑनलाइन deploy और test करना जरूरी है।
इसके बाद इसी hosted app को Android APK में पैक करने का अगला चरण किया जा सकता है। APK में Groq key नहीं रखी जाएगी;
ऐप केवल आपके सुरक्षित online backend को request भेजेगा।

## सीमाएँ
- Chat history अभी server memory में अस्थायी है; server restart होने पर मिट जाएगी।
- Voice सुविधा browser/device support पर निर्भर है। Chrome Android में अनुमति माँगी जा सकती है।
- Free hosting पर पहली request आने पर server को शुरू होने में समय लग सकता है।
