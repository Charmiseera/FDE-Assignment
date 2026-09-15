import { describe, it, expect } from 'vitest';
import { buildHtmlArtifactPrompt } from '../src/server.js';

describe('Prompt building unit tests', () => {
  const mockChunks = [
    {
      source_file: 'elena-verna/transcript.md',
      episode_title: '10 growth tactics that never work | Elena Verna',
      chunk_text: 'Product-led growth activation requires clear habit loops and value delivery early in user onboarding.',
    },
  ];

  const mockConversation = [
    { role: 'user' as const, content: 'How do we improve product activation?' },
    { role: 'assistant' as const, content: 'Focus on habit loops and early value milestones.' },
    { role: 'user' as const, content: 'Create an HTML component displaying this activation framework.' },
  ];

  it('buildHtmlArtifactPrompt formats context and last user directive correctly', () => {
    const prompt = buildHtmlArtifactPrompt(mockChunks, mockConversation);

    expect(prompt).toContain('Create a complete, self-contained HTML/CSS visual artifact');
    expect(prompt).toContain('Create an HTML component displaying this activation framework.');
    expect(prompt).toContain('[10 growth tactics that never work | Elena Verna]');
    expect(prompt).toContain('Product-led growth activation requires clear habit loops');
  });
});
