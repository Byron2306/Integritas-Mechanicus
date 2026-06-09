import { circleAI } from '../circleAI';
import { dataDrive } from '../dataDrive';
import { MemoryBus } from '../memory';

export async function runBenchTest() {
  const startTime = Date.now();
  const samples = [
    { text: "This is a sample human text for forensic benchmarking.", expected: "HUMAN" },
    { text: "The artificial intelligence generated this sentence for testing purposes.", expected: "AI" }
  ];

  const results: any[] = [];
  
  for (let i = 0; i < 3; i++) {
    const cycleStart = Date.now();
    console.log(`[Bench] Starting cycle ${i+1}...`);
    
    // Simulate DataDrive ingest
    await dataDrive.ingest(samples[0].text, samples[1].text);
    
    // Run CircleAI cycle
    const circleResult = await circleAI.start({ input: samples[0].text });
    
    const cycleTime = Date.now() - cycleStart;
    results.push({ cycle: i + 1, time: cycleTime, result: circleResult });
    
    MemoryBus.publish('session-events' as any, { 
        type: 'BENCH_MARK_ENTRY', 
        cycle: i + 1, 
        time: cycleTime 
    });
  }

  const totalTime = Date.now() - startTime;
  return { results, totalTime, avgTime: totalTime / 3 };
}
