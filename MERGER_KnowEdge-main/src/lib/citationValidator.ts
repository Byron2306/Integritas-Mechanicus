export interface CitationError {
  type: string;
  text: string;
  suggestion: string;
  rule: string;
}

export interface CitationReport {
  complianceScore: number;
  errors: CitationError[];
  warnings: string[];
  passCount: number;
  failCount: number;
}

class CitationValidatorService {
  async validateText(text: string): Promise<CitationReport> {
    const errors: CitationError[] = [];
    const warnings: string[] = [];
    let passCount = 0;
    let failCount = 0;

    const runCheck = (passed: boolean, errorDetail: CitationError) => {
      if (passed) {
        passCount++;
      } else {
        failCount++;
        errors.push(errorDetail);
      }
    };

    // 1. Author format: Last, F. M. pattern - flag 'FirstName LastName'
    const nameOrderCheck = !/\b[A-Z][a-z]+ [A-Z][a-z]+\b(,|\s\()/.test(text.substring(0, 5000));
    runCheck(nameOrderCheck, {
      type: 'NAME_ORDER',
      text: 'Detected potential FirstName LastName pattern',
      suggestion: 'Use Last, F. M. format',
      rule: 'APA 7.1'
    });

    // 2. Year format: (YYYY)
    const yearCheck = /\(\d{4}\)/.test(text);
    runCheck(yearCheck, {
      type: 'YEAR_FORMAT',
      text: 'Missing or malformed year markers',
      suggestion: 'Ensure year is in (YYYY) format',
      rule: 'APA 7.2'
    });

    // 3. DOI Format: https://doi.org/
    const oldDoiCheck = !/dx\.doi\.org/.test(text);
    runCheck(oldDoiCheck, {
      type: 'DOI_FORMAT',
      text: 'Detected legacy dx.doi.org links',
      suggestion: 'Use https://doi.org/ prefix',
      rule: 'APA 7.10'
    });

    // 4. Ampersand in in-text citations
    const ampersandCheck = !/\([A-Z,a-z\s]+ and [A-Z,a-z\s]+, \d{4}\)/.test(text);
    runCheck(ampersandCheck, {
      type: 'AMPER_CHECK',
      text: "Found 'and' inside citation parentheses",
      suggestion: "Use '&' inside parentheses",
      rule: 'APA 8.17'
    });

    // 5. Et al punctuation
    const etAlCheck = !/et al(?!(\.))/.test(text);
    runCheck(etAlCheck, {
      type: 'ET_AL_PUNC',
      text: "Detected 'et al' missing a period",
      suggestion: "Always use 'et al.'",
      rule: 'APA 8.17'
    });

    // 6. DOI requirement
    const doiPresentCheck = /doi:|https:\/\/doi\.org/.test(text.toLowerCase());
    runCheck(doiPresentCheck, {
      type: 'DOI_MISSING',
      text: "No DOIs detected in references",
      suggestion: "Add DOIs where available",
      rule: 'APA 9.35'
    });

    // 7. Retrieved from format
    const retrievedCheck = !(text.includes('Retrieved from') && !text.includes('access date'));
    runCheck(retrievedCheck, {
      type: 'WEBSITE_RETR',
      text: "'Retrieved from' often requires an access date for dynamic sources",
      suggestion: "Add access date if the source is likely to change",
      rule: 'APA 9.16'
    });

    // 8. Page number format
    const pageFormatCheck = !/\bpages? \d+\b/i.test(text); // Flag 'page 5' instead of 'p. 5'
    runCheck(pageFormatCheck, {
      type: 'PAGE_FORMAT',
      text: "Used 'page' instead of 'p.' or 'pp.'",
      suggestion: "Use 'p.' or 'pp.' prefix",
      rule: 'APA 8.13'
    });

    // 9. Publisher check (Books)
    const publisherCheck = !/(\(20\d{2}\)\. [^.]+\. [^.]+:\s[^.]+)/.test(text); // Basic check for city: publisher
    if (!publisherCheck) warnings.push("Verify book citations include Publisher info.");

    // 10. Title Case Consistency
    const titleCaseCheck = !/[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+ (Chapter|Article)/.test(text); 
    runCheck(titleCaseCheck, {
      type: 'TITLE_CASE',
      text: "Chapter/Article titles should be sentence case",
      suggestion: "Lowercase secondary words in titles",
      rule: 'APA 6.17'
    });

    const totalChecks = passCount + failCount;
    const complianceScore = totalChecks > 0 ? Number(((passCount / totalChecks) * 100).toFixed(1)) : 0;

    return {
      complianceScore,
      errors,
      warnings,
      passCount,
      failCount
    };
  }
}

export const citationValidator = new CitationValidatorService();
