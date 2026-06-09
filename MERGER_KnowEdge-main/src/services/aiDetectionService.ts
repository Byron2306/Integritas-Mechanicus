import { memory, MemoryLayer, MemoryBus } from '../lib/memory';

export interface DetectionResult {
  provider: string;
  score: number; // 0 to 1, where 1 is highly likely AI
  label: string;
  details?: string;
}

export interface ForensicReport {
  verdict: 'HUMAN' | 'AI' | 'MIXED';
  confidence: number;
  breakdown: DetectionResult[];
  telemetry: any;
  recommendations: string[];
}

/**
 * AI Detection Service - Forensic Pipeline V4.3
 * Implements pure TS offline-capable NLP heuristics.
 */

export class AIDetectionService {
  /**
   * Token-level log-probability approximation using a static bigram frequency model.
   * Calibrated for common academic English.
   */
  static computePerplexity(text: string): number {
    const tokens = text.toLowerCase().match(/\w+/g) || [];
    if (tokens.length < 5) return 100;
    
    // Very simplified log-prob model based on common academic transition frequencies
    let logProbSum = 0;
    for (let i = 0; i < tokens.length - 1; i++) {
      const bigram = `${tokens[i]} ${tokens[i+1]}`;
      // In a real model, we'd lookup bigram frequency. Here we simulate:
      const prob = this.getSimulatedBigramProb(bigram);
      logProbSum += Math.log(prob);
    }
    
    const perplexity = Math.exp(-logProbSum / tokens.length);
    return Math.min(perplexity, 500); // Caps for normalized scoring
  }

  private static getSimulatedBigramProb(bigram: string): number {
    const commonAIFragments = ['furthermore the', 'it is', 'moreover the', 'in conclusion', 'the results', 'this suggests'];
    if (commonAIFragments.some(f => bigram.includes(f))) return 0.45; // High probability = low perplexity = AI likely
    return 0.15; // Low probability = high perplexity = Human likely
  }

  /**
   * CV Squared: Variance of sentence lengths divided by the mean squared.
   */
  static computeBurstiness(text: string): number {
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    if (sentences.length < 2) return 0.5;
    
    const lengths = sentences.map(s => s.trim().split(/\s+/).length);
    const mean = lengths.reduce((a, b) => a + b, 0) / lengths.length;
    const variance = lengths.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / lengths.length;
    
    return variance / (Math.pow(mean, 2) || 1);
  }

  /**
   * TTR (Type-Token Ratio) with moving window of 50 tokens.
   */
  static computeLexicalDiversity(text: string): number {
    const tokens = text.toLowerCase().match(/\w+/g) || [];
    if (tokens.length < 50) return (new Set(tokens).size / (tokens.length || 1));
    
    const windowSize = 50;
    let ttrSum = 0;
    for (let i = 0; i < tokens.length - windowSize; i+=10) {
      const window = tokens.slice(i, i + windowSize);
      ttrSum += new Set(window).size / windowSize;
    }
    return ttrSum / (Math.floor((tokens.length - windowSize)/10) || 1);
  }

  /**
   * Detects top overused AI trigrams (2025 Benchmarks).
   */
  static detectTrigrams(text: string): string[] {
    const aiTrigrams = [
      'it is essential', 'at the same', 'furthermore it is', 'in conclusion the',
      'the impact of', 'to ensure that', 'important to note', 'on the other',
      'this study aims', 'the results suggest'
    ];
    return aiTrigrams.filter(trigram => text.toLowerCase().includes(trigram));
  }

  /**
   * Forensic Aggregator: Weights all internal simulations.
   */
  static async runFullPipeline(text: string): Promise<ForensicReport> {
    const ppl = this.computePerplexity(text); // AI < 35
    const burst = this.computeBurstiness(text); // AI < 0.4
    const ld = this.computeLexicalDiversity(text); // AI < 0.5
    const trigrams = this.detectTrigrams(text);

    const breakdown: DetectionResult[] = [
      {
        provider: 'GPTZero Simulation',
        score: ppl < 35 ? 0.95 : 0.1,
        label: ppl < 35 ? 'AI' : 'HUMAN',
        details: `Perplexity: ${ppl.toFixed(2)}`
      },
      {
        provider: 'ZeroGPT Simulation',
        score: (burst < 0.4 && ppl < 45) ? 0.9 : 0.2,
        label: (burst < 0.4 && ppl < 45) ? 'AI' : 'HUMAN',
        details: `Burstiness: ${burst.toFixed(2)}`
      },
      {
        provider: 'Grammarly Simulation',
        score: ld < 0.45 ? 0.75 : 0.25,
        label: ld < 0.45 ? 'AI' : 'HUMAN',
        details: `Lexical Diversity: ${ld.toFixed(2)}`
      },
      {
        provider: 'Originality.ai Simulation',
        score: (trigrams.length > 2 || ppl < 30) ? 0.98 : 0.05,
        label: (trigrams.length > 2 || ppl < 30) ? 'AI' : 'HUMAN',
        details: `Trigrams Found: ${trigrams.length}`
      }
    ];

    const avgScore = breakdown.reduce((a, b) => a + b.score, 0) / breakdown.length;
    
    const report: ForensicReport = {
      verdict: avgScore > 0.7 ? 'AI' : (avgScore > 0.3 ? 'MIXED' : 'HUMAN'),
      confidence: avgScore > 0.5 ? avgScore : (1 - avgScore),
      breakdown,
      telemetry: {
        charCount: text.length,
        tokenCount: text.split(/\s+/).length,
        entropy: -ld * Math.log2(ld || 0.01) // Crude entropy
      },
      recommendations: []
    };

    if (report.verdict === 'AI') {
      report.recommendations.push("Increase lexical diversity by using domain-specific synonyms.");
      report.recommendations.push("Variable sentence structure is required to improve burstiness.");
    }

    // Save to MemoryBus
    MemoryBus.publish('agent-findings', { type: 'DETECTION_REPORT', data: report });
    memory.write(MemoryLayer.L1, `detection_${Date.now()}`, report, { channel: 'agent-findings' });

    return report;
  }
}

