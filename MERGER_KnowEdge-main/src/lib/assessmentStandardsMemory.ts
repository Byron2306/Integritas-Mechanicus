import { memory, MemoryLayer } from './memory';

export interface AssessmentRubric {
  id: string;
  level: 'MEd' | 'PhD' | 'EdD';
  criteria: Array<{
    name: string;
    description: string;
    weight?: number;
  }>;
}

export interface MarkingBand {
  label: string;
  range: string;
  description: string;
  color: string;
}

class AssessmentStandardsService {
  private lastUpdate: number = 0;
  private rubrics: AssessmentRubric[] = [
    {
      id: 'nwu-med-rubric',
      level: 'MEd',
      criteria: [
        { name: 'Research-worthiness', description: 'Problem statement and significance.' },
        { name: 'Literature review', description: 'Depth and relevance of sources.' },
        { name: 'Theoretical framework', description: 'Application of theory.' },
        { name: 'Research methods', description: 'Design, sampling, and ethics.' },
        { name: 'Logical structure', description: 'Coherence and flow.' },
        { name: 'Language/style', description: 'Academic tone and accuracy.' },
        { name: 'Original contribution', description: 'Contribution to knowledge.' }
      ]
    },
    {
      id: 'nwu-phd-rubric',
      level: 'PhD',
      criteria: [
        { name: 'Original Contribution', description: 'Significant new knowledge.' },
        { name: 'Rigorous Methodology', description: 'Advanced research design.' },
        { name: 'Theoretical Mastery', description: 'Critical engagement with theory.' },
        { name: 'Technical Standards', description: 'Formatting and references.' }
      ]
    }
  ];

  private markingBands: MarkingBand[] = [
    { label: 'Distinction', range: '75%+', description: 'Exceptional work, publishable quality.', color: 'emerald' },
    { label: 'Merit', range: '65-74%', description: 'Strong work with minor revisions.', color: 'cyan' },
    { label: 'Satisfactory', range: '50-64%', description: 'Acceptable work with notable improvements needed.', color: 'yellow' },
    { label: 'Inadequate', range: '<50%', description: 'Major deficiencies, requires substantial rewrite.', color: 'red' }
  ];

  constructor() {
    // constructor side-effects removed to prevent circular dependency TDZ
  }

  getStandards() {
    return {
      rubrics: this.rubrics,
      markingBands: this.markingBands
    };
  }

  getRubric(level: 'MEd' | 'PhD' | 'EdD'): AssessmentRubric | undefined {
    return this.rubrics.find(r => r.level === level) || this.rubrics[0];
  }

  getMarkingBands() {
    return this.markingBands;
  }

  async refreshStandards() {
    this.lastUpdate = Date.now();
    memory.write(MemoryLayer.L2, "assessment_standards_last_refresh", this.lastUpdate);
    memory.write(MemoryLayer.L2, "assessment_standards_data", {
      rubrics: this.rubrics,
      markingBands: this.markingBands
    });
    console.debug('[Assessment Standards Memory] Refreshed');
  }
}

export const assessmentStandards = new AssessmentStandardsService();
