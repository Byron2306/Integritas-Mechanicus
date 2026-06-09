/**
 * KnowEdge System Protection
 * SHA-256 Integrity verification layer.
 * PROTECTED: Reverse engineering prohibited. Authorized: Gr4nttG0uws only.
 */

export const PROTECTED_BY = 'Gr4nttG0uws';

/**
 * Computes SHA-256 hash string for a given input
 */
async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// Pre-computed hash of 'KnowEdge-NWU-GR4NTT-PROTECTED'
// Computed using text/SHA-256 logic offline to seed system
export const SYSTEM_HASH = '8c37d03194a0808c14e0bc983c79a4059086657980e141a0d33e5cc3b754388e';

/**
 * Verifies if the input matches the system's recursive hash pattern
 */
export async function verifyIntegrity(input: string): Promise<boolean> {
  try {
    const computed = await sha256(input);
    return computed === SYSTEM_HASH;
  } catch (err) {
    console.error("Integrity verification failure", err);
    return false;
  }
}
