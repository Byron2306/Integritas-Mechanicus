import { GoogleGenerativeAI } from "@google/generative-ai";
import { nwuPolicyMemory, PolicyChecker } from './nwuPolicyMemory';
import { assessmentStandards } from './assessmentStandardsMemory';
import { citationValidator, CitationReport } from './citationValidator';
import { AIDetectionService, ForensicReport } from '../services/aiDetectionService';
import { memory, MemoryLayer, MemoryBus } from './memory';
import JSZip from 'jszip';

export interface TrackChange {
  id: string;
  type: 'insertion' | 'deletion' | 'comment';
  originalText: string;
  suggestedText: string;
  reason: string;
  reviewer: string;
  position: number;
  category: string;
}

export interface ReviewDocument {
  title: string;
  overallAssessment: string;
  score: number;
  criteriaScores: Record<string, number>;
  feedback: string;
  recommendation: string;
  trackChanges: TrackChange[];
}

export interface ERTPReviewResult {
  supervisor: ReviewDocument;
  reader1: ReviewDocument;
  reader2: ReviewDocument;
  forensicReport?: ForensicReport;
  policyReport?: any;
}

export type ERTPProgressCallback = (stage: number, label: string, percent: number) => void;

class ERTPReviewService {
  private ai = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || "");

  /**
   * Autonomous 7-Stage ERTP Pipeline V4.3
   */
  async runFullERTPPipeline(
    sourceText: string,
    degreeLevel: 'MEd' | 'PhD' | 'EdD',
    onProgress?: ERTPProgressCallback
  ): Promise<ERTPReviewResult> {
    
    // Stage 1: Pre-flight checks
    onProgress?.(1, "Pre-flight checks...", 5);
    if (sourceText.length < 500) throw new Error("Document too short for forensic review.");
    await new Promise(r => setTimeout(r, 3000));

    // Stage 2: AI Integrity Guard (NLP Metrics)
    onProgress?.(2, "AI Integrity Guard (NLP Metrics)...", 20);
    const forensicReport = await AIDetectionService.runFullPipeline(sourceText);
    MemoryBus.publish('agent-findings', { stage: 2, forensicReport });
    await new Promise(r => setTimeout(r, 3000));

    // Stage 3: Citation Validator (Format & Integrity)
    onProgress?.(3, "Citation Validator (APA 7th)...", 35);
    const citationReport = await citationValidator.validateText(sourceText);
    MemoryBus.publish('agent-findings', { stage: 3, citationReport });
    await new Promise(r => setTimeout(r, 3000));

    // Stage 4: NWU Policy Alignment (Clause 5.1-5.4)
    onProgress?.(4, "NWU Policy Alignment Analysis...", 50);
    const policyReport = PolicyChecker.checkText(sourceText);
    MemoryBus.publish('agent-findings', { stage: 4, policyReport });
    await new Promise(r => setTimeout(r, 3000));

    // Stage 5: Socratic Reader 1 (Structural Audit)
    onProgress?.(5, "Generating Socratic Reader 1 (Structure)...", 65);
    const reader1 = await this.generateReaderReport(sourceText, degreeLevel, "Structural Auditor", forensicReport, citationReport);
    await new Promise(r => setTimeout(r, 3000));

    // Stage 6: Socratic Reader 2 (Integrity Synthesis)
    onProgress?.(6, "Generating Socratic Reader 2 (Integrity Spec)...", 85);
    const reader2 = await this.generateReaderReport(sourceText, degreeLevel, "Integrity Specialist", forensicReport, citationReport, policyReport);
    await new Promise(r => setTimeout(r, 3000));

    // Stage 7: Final Assembly & Supervisor Guidance
    onProgress?.(7, "Final Report Assembly...", 95);
    const supervisor = await this.generateReaderReport(sourceText, degreeLevel, "Primary Supervisor", forensicReport, citationReport, policyReport);
    await new Promise(r => setTimeout(r, 3000));

    const result: ERTPReviewResult = {
      supervisor,
      reader1,
      reader2,
      forensicReport,
      policyReport
    };

    onProgress?.(8, "Pipeline Complete", 100);
    MemoryBus.publish('session-events', { type: 'ERTP_PIPELINE_COMPLETE', result });
    
    return result;
  }

  private async generateReaderReport(
    text: string, 
    level: string, 
    persona: string, 
    forensic?: ForensicReport, 
    citation?: CitationReport,
    policy?: any
  ): Promise<ReviewDocument> {
    const policies = nwuPolicyMemory.getAllPolicies();
    const rubric = assessmentStandards.getRubric(level as any);
    
    const prompt = `
      You are the ${persona} for a ${level} thesis review at NWU.
      
      NWU Policies: ${JSON.stringify(policies)}
      Rubric: ${JSON.stringify(rubric)}
      
      Forensic Feed:
      - AI Detection: ${forensic?.verdict} (Confidence: ${forensic?.confidence})
      - Citation Health: ${citation?.complianceScore}%
      - Policy Score: ${policy?.score}%
      
      Document Snapshot: ${text.substring(0, 10000)}...
      
      Generate a detailed ReviewDocument in JSON format with fields:
      title, overallAssessment, score (0-100), criteriaScores (Object), feedback, recommendation, trackChanges (Array of TrackChange objects).
    `;

  const model = this.ai.getGenerativeModel({ model: "gemini-2.0-flash" });
    const result = await model.generateContent(prompt);
    const response = await result.response;
    const jsonStr = response.text().replace(/```json|```/g, '');
    
    try {
      return JSON.parse(jsonStr);
    } catch (e) {
      console.error("JSON parse failed for reader report", e);
      return {
        title: `${persona} Report`,
        overallAssessment: "DRAFT ASSESSMENT: Parsing error occurred.",
        score: 0,
        criteriaScores: {},
        feedback: response.text(),
        recommendation: "RE-RUN PIPELINE",
        trackChanges: []
      };
    }
  }

  async generateZipPackage(review: ERTPReviewResult): Promise<string> {
    const zip = new JSZip();
    
    zip.file("supervisor_report.md", `# Supervisor Report\n\n${review.supervisor.overallAssessment}\n\nFeedback:\n${review.supervisor.feedback}`);
    zip.file("reader_1.md", `# Reader 1 report\n\n${review.reader1.overallAssessment}`);
    zip.file("reader_2.md", `# Reader 2 report\n\n${review.reader2.overallAssessment}`);
    zip.file("forensic_audit.json", JSON.stringify(review.forensicReport, null, 2));
    zip.file("compliance_report.json", JSON.stringify(review.policyReport, null, 2));

    const content = await zip.generateAsync({ type: "base64" });
    return content;
  }
}

export const ertpReview = new ERTPReviewService();
