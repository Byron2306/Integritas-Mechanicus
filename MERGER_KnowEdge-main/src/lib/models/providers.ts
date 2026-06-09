export interface EmbeddingProvider {
  readonly name: string;
  embed(text: string, opts?: { isQuery?: boolean; title?: string }): Promise<number[] | null>;
  embedBatch(texts: string[], opts?: { isQuery?: boolean; titles?: string[] }): Promise<(number[] | null)[]>;
}

export interface RerankProvider {
  readonly name: string;
  rerank(
    query: string,
    documents: Array<{ file: string; text: string; title?: string }>
  ): Promise<Array<{ file: string; score: number }>>;
}

export interface GenerateProvider {
  readonly name: string;
  expandQuery(
    query: string,
    opts?: { intent?: string }
  ): Promise<Array<{ type: 'lex' | 'vec' | 'hyde'; text: string }>>;
}

export class MockEmbeddingProvider implements EmbeddingProvider {
  readonly name = 'mock-lattice-embed';
  async embed(text: string) { return new Array(1536).fill(0).map(() => Math.random()); }
  async embedBatch(texts: string[]) { return texts.map(() => new Array(1536).fill(0).map(() => Math.random())); }
}

export class MockRerankProvider implements RerankProvider {
  readonly name = 'mock-lattice-rerank';
  async rerank(query: string, documents: any[]) {
    return documents.map(d => ({ file: d.file, score: Math.random() }));
  }
}

export class MockGenerateProvider implements GenerateProvider {
  readonly name = 'mock-lattice-gen';
  async expandQuery(query: string) {
    const results: Array<{ type: 'lex' | 'vec' | 'hyde'; text: string }> = [
      { type: 'lex', text: query },
      { type: 'vec', text: `semantic concept of ${query}` },
      { type: 'hyde', text: `Hypothetical answer to: ${query}` }
    ];
    return results;
  }
}
