export interface IntegrityReport {
  status: 'PASS' | 'WARN' | 'FAIL';
  flags: string[];
  policyRefs: string[];
  aiScore: number;
  personalVoiceScore: number;
  citationDensity: number;
}

class AIIntegrityGuardService {
  async scanText(text: string): Promise<IntegrityReport> {
    const flags: string[] = [];
    let aiScore = 0;

    // 1. Repetitive phrase detection (3-gram patterns)
    const words = text.toLowerCase().match(/\b(\w+)\b/g) || [];
    const trigrams: Record<string, number> = {};
    let trigramCount = 0;
    for (let i = 0; i < words.length - 2; i++) {
      const tri = `${words[i]} ${words[i+1]} ${words[i+2]}`;
      trigrams[tri] = (trigrams[tri] || 0) + 1;
      trigramCount++;
    }
    const repeated = Object.values(trigrams).filter(c => c > 1).reduce((a, b) => a + b, 0);
    const repetitionRate = trigramCount > 0 ? (repeated / trigramCount) * 100 : 0;
    if (repetitionRate > 15) {
      flags.push(`High repetition rate (${repetitionRate.toFixed(1)}%) detected.`);
      aiScore += 20;
    }

    // 2. Personal voice check (first-person pronouns)
    const firstPerson = (text.match(/\b(I|me|my|mine|we|us|our|ours)\b/gi) || []).length;
    const personalVoiceScore = Math.min(100, (firstPerson / (words.length / 100)) * 20);
    if (personalVoiceScore < 5) {
      flags.push("Low personal voice profile - text appears overly detached.");
      aiScore += 15;
    }

    // 3. Citation density check
    const citations = (text.match(/\([A-Z][a-z]+, \d{4}\)|\[\d+\]/g) || []).length;
    const citationDensity = citations / (words.length / 300);
    if (citationDensity < 1) {
      flags.push(`Critical citation gap (${citationDensity.toFixed(2)} per 300 words).`);
      aiScore += 25;
    }

    // 4. Transition word overuse
    const transitions = (text.match(/\b(Furthermore|Moreover|Additionally|Consequently|In addition)\b/gi) || []).length;
    const transitionDensity = transitions / (words.length / 500);
    if (transitionDensity > 3) {
      flags.push("Overuse of formal transition markers ('Furthermore', etc).");
      aiScore += 15;
    }

    // 5. Contraction check (Unnaturally perfect)
    const contractions = (text.match(/\b\w+('\w+)\b/g) || []).length;
    if (contractions === 0 && words.length > 500) {
      flags.push("Absence of contractions indicates clinical/synthetic tone.");
      aiScore += 10;
    }

    let status: 'PASS' | 'WARN' | 'FAIL' = 'PASS';
    if (aiScore > 60) status = 'FAIL';
    else if (aiScore >= 30) status = 'WARN';

    return {
      status,
      flags,
      policyRefs: [
        'NWU AI Policy 5P_5.10 (2025)',
        'NWU Academic Integrity Policy (2024)'
      ],
      aiScore,
      personalVoiceScore,
      citationDensity
    };
  }
}

export const aiIntegrityGuard = new AIIntegrityGuardService();
