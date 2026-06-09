import { 
  GoogleGenAI, 
  ThinkingLevel, 
  Type, 
  Modality,
  GenerateContentResponse
} from "@google/genai";
import { ENGINE_310_ZD } from "../constants";

const API_KEY = process.env.GEMINI_API_KEY || "";

export const getAI = () => {
  if (!API_KEY) {
    console.warn("GEMINI_API_KEY is not defined. AI features may not work.");
  }
  return new GoogleGenAI({ apiKey: API_KEY });
};

export type VerificationStatus = 'Verified' | 'Unverified' | 'Conflicted';

export interface GroundingSource {
  title: string;
  uri: string;
  status: VerificationStatus;
}

function verifySource(title: string, uri: string): VerificationStatus {
  const { trusted_domains, conflict_keywords } = ENGINE_310_ZD.references_pack;
  
  const lowerTitle = title.toLowerCase();
  const hasConflict = conflict_keywords.some(kw => lowerTitle.includes(kw));
  if (hasConflict) return 'Conflicted';

  try {
    const url = new URL(uri);
    const domain = url.hostname.replace('www.', '');
    const isTrusted = trusted_domains.some(td => domain === td || domain.endsWith('.' + td));
    
    // Also check URL path for conflict keywords
    const hasUrlConflict = conflict_keywords.some(kw => url.pathname.toLowerCase().includes(kw));
    if (hasUrlConflict) return 'Conflicted';

    if (isTrusted) return 'Verified';
  } catch (e) {
    // Invalid URL
  }

  return 'Unverified';
}

// 1. Chatbot with Thinking Mode
export async function chatWithThinking(message: string, useThinking: boolean = false, systemInstruction?: string, files?: { mimeType: string, data: string }[]) {
  const ai = getAI();
  const model = "gemini-3.1-pro-preview";
  
  const parts: any[] = [{ text: message }];
  if (files && files.length > 0) {
    files.forEach(f => {
      parts.push({
        inlineData: {
          mimeType: f.mimeType,
          data: f.data
        }
      });
    });
  }

  const response = await ai.models.generateContent({
    model,
    contents: { parts },
    config: {
      systemInstruction,
      ...(useThinking ? { thinkingConfig: { thinkingLevel: ThinkingLevel.HIGH } } : {})
    }
  });

  return response.text;
}

// 2. Fast AI Responses (Upgraded to High Thinking for Full Neural Upgrade)
export async function fastResponse(message: string) {
  return chatWithThinking(message, true, "Perform a high-speed but deep architectural analysis.");
}

// 3. Search Grounding
export async function searchGroundedQuery(query: string, systemInstruction?: string) {
  const ai = getAI();
  const model = "gemini-3-flash-preview";
  
  const response = await ai.models.generateContent({
    model,
    contents: query,
    config: {
      systemInstruction,
      tools: [{ googleSearch: {} }]
    }
  });

  const rawSources = response.candidates?.[0]?.groundingMetadata?.groundingChunks || [];
  const verifiedSources: GroundingSource[] = rawSources.map((chunk: any) => {
    const title = chunk.web?.title || "Unknown Source";
    const uri = chunk.web?.uri || "";
    return {
      title,
      uri,
      status: verifySource(title, uri)
    };
  });

  return {
    text: response.text,
    sources: verifiedSources
  };
}

// 4. Text-to-Speech
export async function generateSpeech(text: string) {
  const ai = getAI();
  const model = "gemini-2.5-flash-preview-tts";
  
  const response = await ai.models.generateContent({
    model,
    contents: [{ parts: [{ text }] }],
    config: {
      responseModalities: [Modality.AUDIO],
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: { voiceName: 'Kore' },
        },
      },
    },
  });

  return response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
}

// 5. Audio Transcription (Simplified for demo)
export async function transcribeAudio(base64Audio: string, mimeType: string = "audio/webm") {
  const ai = getAI();
  const model = "gemini-3-flash-preview";
  
  const response = await ai.models.generateContent({
    model,
    contents: {
      parts: [
        {
          inlineData: {
            mimeType: mimeType,
            data: base64Audio
          }
        },
        { text: "Transcribe this audio exactly." }
      ]
    }
  });

  return response.text;
}

// 6. Vector Embeddings
export async function generateEmbedding(content: string | object) {
  const ai = getAI();
  const model = "gemini-embedding-2-preview";
  
  const text = typeof content === 'string' ? content : JSON.stringify(content);
  
  const result = await ai.models.embedContent({
    model,
    contents: [text]
  });

  return result.embeddings[0].values;
}

// 7. Image Generation (Imagen)
export async function generateArchitectureImage(prompt: string) {
  const ai = getAI();
  const model = "imagen-4.0-generate-001";
  
  const response = await ai.models.generateImages({
    model,
    prompt,
    config: {
      numberOfImages: 1,
      outputMimeType: 'image/jpeg',
      aspectRatio: '1:1',
    },
  });

  const base64EncodeString = response.generatedImages[0].image.imageBytes;
  return `data:image/jpeg;base64,${base64EncodeString}`;
}
