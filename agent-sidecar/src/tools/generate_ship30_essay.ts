export interface ValidationResult {
  passed: boolean;
  word_count: number;
  subheadings_count: number;
  has_bold: boolean;
  has_takeaway: boolean;
  unmet_criteria: string[];
}

export function validateEssay(markdown: string): ValidationResult {
  const unmet_criteria: string[] = [];

  // Word count calculation (filtering out markdown symbols and whitespace)
  const words = markdown
    .trim()
    .replace(/[#*_`~>-]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 0);
  const word_count = words.length;

  // PRD & Plan requirement: 1,250 words ± 15% -> [1063, 1438]
  const MIN_WORDS = 1063;
  const MAX_WORDS = 1438;
  if (word_count < MIN_WORDS) {
    unmet_criteria.push(
      `Word count (${word_count}) is below minimum target of ${MIN_WORDS} words (1,250 ± 15%)`
    );
  } else if (word_count > MAX_WORDS) {
    unmet_criteria.push(
      `Word count (${word_count}) exceeds maximum target of ${MAX_WORDS} words (1,250 ± 15%)`
    );
  }

  // Check subheadings: at least 2 headers (## or ###)
  const headingMatches = markdown.match(/^#{2,3}\s+.+$/gm) || [];
  const subheadings_count = headingMatches.length;
  if (subheadings_count < 2) {
    unmet_criteria.push(
      `Found ${subheadings_count} subheadings; Ship 30/30 requires at least 2 distinct subheadings`
    );
  }

  // Check bold emphasis: at least one **bold text**
  const has_bold = /\*\*[^*]+\*\*/.test(markdown);
  if (!has_bold) {
    unmet_criteria.push("Requires selective bold emphasis (**key phrase**) for skimmability");
  }

  // Check identifiable takeaway
  const takeawayRegex = /(takeaway|the bottom line|key insight|core lesson)/i;
  const has_takeaway = takeawayRegex.test(markdown);
  if (!has_takeaway) {
    unmet_criteria.push("Requires an identifiable takeaway or key insight section");
  }

  return {
    passed: unmet_criteria.length === 0,
    word_count,
    subheadings_count,
    has_bold,
    has_takeaway,
    unmet_criteria,
  };
}

export interface EssayGenerationOutput {
  title: string;
  content: string;
  validation_status: {
    passed: boolean;
    word_count: number;
    unmet_criteria: string[];
  };
}
