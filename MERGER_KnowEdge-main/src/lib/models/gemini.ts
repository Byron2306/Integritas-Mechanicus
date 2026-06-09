import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from "@google/generative-ai";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || "");

export interface GeminiOptions {
  model?: string;
  temperature?: number;
  topK?: number;
  topP?: number;
  maxOutputTokens?: number;
  tools?: any[];
}

export async function callGemini(prompt: string, options: GeminiOptions = {}) {
  const modelId = options.model || "gemini-2.0-flash";
  const model = genAI.getGenerativeModel({
    model: modelId,
    generationConfig: {
      temperature: options.temperature ?? 0.7,
      topK: options.topK,
      topP: options.topP,
      maxOutputTokens: options.maxOutputTokens,
    },
    safetySettings: [
      { category: HarmCategory.HARM_CATEGORY_HARASSMENT, threshold: HarmBlockThreshold.BLOCK_NONE },
      { category: HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold: HarmBlockThreshold.BLOCK_NONE },
      { category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold: HarmBlockThreshold.BLOCK_NONE },
      { category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold: HarmBlockThreshold.BLOCK_NONE },
    ],
    tools: options.tools,
  });

  try {
    const result = await model.generateContent(prompt);
    const response = await result.response;
    return response.text();
  } catch (e) {
    console.error(`[Gemini] Error calling ${modelId}:`, e);
    throw e;
  }
}

export async function callGeminiChat(messages: any[], options: GeminiOptions = {}) {
  const modelId = options.model || "gemini-2.0-flash";
  const model = genAI.getGenerativeModel({ model: modelId, tools: options.tools });
  const chat = model.startChat({
    history: messages.slice(0, -1),
    generationConfig: {
      temperature: options.temperature ?? 0.7,
    },
  });

  try {
    const lastMessage = messages[messages.length - 1].parts[0].text;
    const result = await chat.sendMessage(lastMessage);
    const response = await result.response;
    return response.text();
  } catch (e) {
    console.error(`[GeminiChat] Error calling ${modelId}:`, e);
    throw e;
  }
}
