// KnowEdge Merger Integration Module v1.0.0
// Compatible: Node.js 18+, Browser ESM, PowerShell via WebRequest
/*
  PowerShell usage example:
  $body = @{ phase="ANALYZE"; progress=60 } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri "http://localhost:3000/api/v1/runs/default/transition" -Body $body -ContentType "application/json"
*/

class KnowEdgeIntegration {
  constructor(baseUrl = '', apiKey = '') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
  }

  async _fetch(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      timeout: 10000
    };

    try {
      const response = await fetch(url, { ...defaultOptions, ...options });
      if (!response.ok) {
        throw new Error(`KnowEdge API Error: ${response.status} ${response.statusText}`);
      }
      return await response.json();
    } catch (err) {
      console.error(`KnowEdge fetch failure [${path}]:`, err);
      throw err;
    }
  }

  async getRunStatus(runId) {
    return this._fetch(`/api/v1/runs/${runId}`);
  }

  async getHeartbeat(runId) {
    return this._fetch(`/api/v1/runs/${runId}/heartbeat`);
  }

  async getDecisionLedger(runId) {
    return this._fetch(`/api/v1/runs/${runId}/memory`);
  }

  async transitionPhase(runId, phase, progress) {
    return this._fetch(`/api/v1/runs/${runId}/transition`, {
      method: 'POST',
      body: JSON.stringify({ phase, progress })
    });
  }

  async submitForAnalysis(content) {
    return this._fetch('/api/mistral/generate', {
      method: 'POST',
      body: JSON.stringify({ prompt: content })
    });
  }

  async getCircleAIResult(content) {
    return this._fetch('/api/circleai/detect', {
      method: 'POST',
      body: JSON.stringify({ text: content })
    });
  }

  async getDataDrivenAnalytics() {
    return this._fetch('/api/datadriven/analytics');
  }
}

// Export for Node.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { KnowEdgeIntegration };
}

// Export for Browser
if (typeof window !== 'undefined') {
  window.KnowEdgeIntegration = KnowEdgeIntegration;
}
