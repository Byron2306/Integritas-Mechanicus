import fs from 'fs';
import path from 'path';
import { FineWebRecord } from '../ingest/internalFineWeb';
import { EmbeddingProvider, RerankProvider, GenerateProvider, MockEmbeddingProvider, MockRerankProvider, MockGenerateProvider } from '../models/providers';

export interface LatticeSearchOptions {
  limit?: number;
  useExpansion?: boolean;
  rerankBatch?: number;
}

export class LatticeRetrievalKernel {
  private artifacts: Map<string, any> = new Map();
  private chunks: any[] = [];
  private runDir: string;
  
  // Model Plane
  private embedder: EmbeddingProvider;
  private reranker: RerankProvider;
  private generator: GenerateProvider;

  constructor(runDir: string, providers?: { embedder?: EmbeddingProvider, reranker?: RerankProvider, generator?: GenerateProvider }) {
    this.runDir = runDir;
    this.embedder = providers?.embedder || new MockEmbeddingProvider();
    this.reranker = providers?.reranker || new MockRerankProvider();
    this.generator = providers?.generator || new MockGenerateProvider();
  }

  async indexCorpus(corpusPath: string) {
    // Clear existing to avoid duplicates on re-index in memory
    this.artifacts.clear();
    this.chunks = [];
    
    if (!fs.existsSync(corpusPath)) return;

    const fileContent = fs.readFileSync(corpusPath, 'utf8');
    const lines = fileContent.split('\n').filter(l => l.trim());
    
    for (const line of lines) {
      const record: FineWebRecord = JSON.parse(line);
      
      if (!this.artifacts.has(record.source_sha256)) {
        this.artifacts.set(record.source_sha256, {
          id: record.source_sha256,
          name: record.source_path,
          sha256: record.source_sha256,
          type: record.source_type
        });
      }

      this.chunks.push({
        id: record.record_id,
        artifact_id: record.source_sha256,
        chunk_index: record.chunk_index,
        text: record.text
      });
    }
  }

  async search(query: string, options: LatticeSearchOptions = {}) {
    const limit = options.limit || 10;
    
    // 1. Query Expansion (if enabled)
    let searchBranches = [{ type: 'lex', text: query }];
    if (options.useExpansion) {
      searchBranches = await this.generator.expandQuery(query);
    }

    // 2. Multi-Signal Retrieval
    const lexResults: any[] = [];
    const vecResults: any[] = [];

    for (const branch of searchBranches) {
      if (branch.type === 'lex') {
        lexResults.push(...this.lexicalSearch(branch.text));
      } else {
        // Simulated Vector Search
        vecResults.push(...this.lexicalSearch(branch.text)); 
      }
    }

    // 3. Reciprocal Rank Fusion (RRF)
    const combinedScores = new Map<string, { chunk: any, rrfScore: number }>();
    const k = 60;

    const fuse = (results: any[]) => {
      results.forEach((res, rank) => {
        const id = `${res.artifact_id}_${res.chunk_index}`;
        const current = combinedScores.get(id) || { chunk: res, rrfScore: 0 };
        current.rrfScore += 1 / (k + rank + 1);
        combinedScores.set(id, current);
      });
    };

    fuse(lexResults);
    fuse(vecResults);

    // 4. Sort and Slice Candidates
    const candidates = Array.from(combinedScores.values())
      .sort((a, b) => b.rrfScore - a.rrfScore)
      .slice(0, 20); // Top 20 for reranking

    // 5. Reranking
    const rerankTargets = candidates.map(c => ({
      file: c.chunk.artifact_id,
      text: c.chunk.text,
      title: this.artifacts.get(c.chunk.artifact_id)?.name
    }));

    const reranked = await this.reranker.rerank(query, rerankTargets);
    
    // 6. Merge Signals
    const finalResults = candidates.map(c => {
      const artifact = this.artifacts.get(c.chunk.artifact_id);
      const rerankData = reranked.find(r => r.file === c.chunk.artifact_id);
      
      return {
        text: c.chunk.text,
        artifact_name: artifact ? artifact.name : 'Unknown',
        chunk_index: c.chunk.chunk_index,
        rank: (c.rrfScore * 0.4) + ((rerankData?.score || 0) * 0.6)
      };
    })
    .sort((a, b) => b.rank - a.rank)
    .slice(0, limit);

    return finalResults;
  }

  private lexicalSearch(query: string) {
    const terms = query.toLowerCase().split(/\s+/).filter(q => q.length > 2);
    return this.chunks
      .map(chunk => {
        let score = 0;
        const textLower = chunk.text.toLowerCase();
        for (const term of terms) {
          if (textLower.includes(term)) score += 1;
        }
        return { ...chunk, score };
      })
      .filter(c => c.score > 0)
      .sort((a, b) => b.score - a.score);
  }

  async getStats() {
    return {
      artifacts: this.artifacts.size,
      chunks: this.chunks.length
    };
  }

  close() {
    this.artifacts.clear();
    this.chunks = [];
  }
}
