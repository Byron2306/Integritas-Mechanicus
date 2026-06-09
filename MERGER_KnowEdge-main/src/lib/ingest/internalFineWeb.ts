import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

export interface FineWebRecord {
  record_id: string;
  source_path: string;
  source_type: string;
  source_sha256: string;
  chunk_index: number;
  text: string;
  signals: {
    char_len: number;
    line_count: number;
    word_count: number;
  };
}

export interface DocumentLoader {
  readonly name: string;
  supports(artifact: { name: string, content: string }): boolean;
  load(artifact: { name: string, content: string }): Promise<{ body: string, metadata?: any }>;
}

export class DefaultLoader implements DocumentLoader {
  readonly name = 'default-text-loader';
  supports() { return true; }
  async load(artifact: { content: string }) { return { body: artifact.content }; }
}

export class InternalFineWeb {
  private corpusPath: string;
  private changeLogPath: string;
  private verificationPath: string;
  private errorLogPath: string;
  private knownHashes: Set<string> = new Set();
  private loaders: DocumentLoader[] = [new DefaultLoader()];

  constructor(runDir: string) {
    const ingestDir = path.join(runDir, 'ingest');
    if (!fs.existsSync(ingestDir)) fs.mkdirSync(ingestDir, { recursive: true });

    this.corpusPath = path.join(ingestDir, 'corpus.jsonl');
    this.changeLogPath = path.join(ingestDir, 'ChangeLog.csv');
    this.verificationPath = path.join(ingestDir, 'Verification.md');
    this.errorLogPath = path.join(ingestDir, 'errors.log');

    // Initialize logs
    fs.writeFileSync(this.changeLogPath, 'timestamp,action,file,status\n');
    fs.writeFileSync(this.verificationPath, '# Verification Report\n\n');
    fs.writeFileSync(this.errorLogPath, '');
    
    // Load existing hashes if corpus exists
    if (fs.existsSync(this.corpusPath)) {
       const content = fs.readFileSync(this.corpusPath, 'utf8');
       content.split('\n').filter(l => l.trim()).forEach(line => {
         try {
           const rec = JSON.parse(line);
           this.knownHashes.add(rec.source_sha256);
         } catch {}
       });
    }
  }

  registerLoader(loader: DocumentLoader) {
    this.loaders.unshift(loader);
  }

  async ingest(artifacts: any[]): Promise<void> {
    const timestamp = new Date().toISOString();
    
    for (const artifact of artifacts) {
      try {
        const content = artifact.content || '';
        const sha256 = crypto.createHash('sha256').update(content).digest('hex');
        
        // Content-Addressing: Skip duplicate bodies (Deduplication)
        if (this.knownHashes.has(sha256)) {
          console.log(`[OMEGA] Skipping duplicate content: ${artifact.name} (${sha256})`);
          continue;
        }

        // Loader Selection
        const loader = this.loaders.find(l => l.supports(artifact)) || this.loaders[this.loaders.length - 1];
        const loadedDoc = await loader.load(artifact);
        const processedContent = loadedDoc.body;
        
        const ext = artifact.name?.split('.').pop() || 'txt';
        
        // Chunking
        const chunks = this.chunkText(processedContent, 2000);
        
        chunks.forEach((chunk, index) => {
          const record: FineWebRecord = {
            record_id: `rec_${crypto.randomBytes(4).toString('hex')}_${index}`,
            source_path: artifact.name || 'unknown',
            source_type: ext,
            source_sha256: sha256,
            chunk_index: index,
            text: chunk,
            signals: {
              char_len: chunk.length,
              line_count: chunk.split('\n').length,
              word_count: chunk.split(/\s+/).length
            }
          };
          
          fs.appendFileSync(this.corpusPath, JSON.stringify(record) + '\n');
        });

        this.knownHashes.add(sha256);
        this.logChange(timestamp, 'INGEST', artifact.name, 'SUCCESS');
        this.addVerification(artifact.name, sha256, chunks.length);

      } catch (err: any) {
        fs.appendFileSync(this.errorLogPath, `[${timestamp}] Error ingesting ${artifact.name}: ${err.message}\n`);
        this.logChange(timestamp, 'INGEST', artifact.name, 'FAILED');
      }
    }
  }

  private chunkText(text: string, size: number): string[] {
    const chunks: string[] = [];
    for (let i = 0; i < text.length; i += size) {
      chunks.push(text.substring(i, i + size));
    }
    return chunks.length > 0 ? chunks : [''];
  }

  private logChange(ts: string, action: string, file: string, status: string) {
    fs.appendFileSync(this.changeLogPath, `${ts},${action},${file},${status}\n`);
  }

  private addVerification(file: string, hash: string, chunks: number) {
    fs.appendFileSync(this.verificationPath, `- **File**: ${file}\n  - **SHA256**: \`${hash}\`\n  - **Chunks**: ${chunks}\n  - **Status**: VERIFIED\n\n`);
  }
}
