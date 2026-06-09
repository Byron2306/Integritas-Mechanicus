# EdgeK Agents Guide — KnowEdge Merger V3.1
**Topic: Autonomous Task Execution & Skill Crystallization**

## Summary
EdgeK Agents are the autonomous reasoning engine of KnowEdge Merger V3.1. They replace static automation with a dynamic, state-aware loop capable of managing its own workflow and learning from successful outcomes.

## 1. The Core Loop (PREC)
Every EdgeK Agent operates on a four-stage cycle:
1. **Perceive**: The agent reads the application state, including active artifacts, run status, and recent L2 memory "fluctuations."
2. **Reason**: Utilizing Gemini-3.1 Reasoning, the agent decomposes a user request into a JSON sequence of Atomic Tools.
3. **Execute**: The agent runs the tools sequentially. If a tool fails, the agent can re-perceive and adjust its plan mid-run.
4. **Crystallize**: Upon task success, the execution sequence is distilled into a "Skill" (L3 Memory), allowing for instantaneous re-execution in future sessions.

## 2. The Atomic Toolset (9 Tools)
To maintain security and deterministic behavior, EdgeK Agents are restricted to these 9 atomic operations:
1. `readArtifact(id)`: Read content of any ingested file.
2. `writeOutput(content)`: Update the synthesis display or report buffer.
3. `searchMemory(query)`: Query L2/L4 memory for semantic relevance.
4. `updateCheckpoint(data)`: Save transient state to L1 memory.
5. `startLongtermUpdate(key, value)`: Persist facts to L2 global memory.
6. `scanArtifact(text)`: Trigger the forensic detection pipeline.
7. `runSynthesis(source, target, context)`: Execute the full Omega synthesis pipeline.
8. `askUser(question)`: Request human-in-the-loop clarification (Bridge required).
9. `learnConcept(concept, level)`: Feed data into the Socratic Learning Lab.

## 3. Memory Interaction
- **L1 (Transient)**: Used for rapid checkpointing during a run (e.g. "I have read 3 of 5 files").
- **L2 (Global)**: Used to store reusable session facts (e.g. "User nwuedcc1 prefers formal synthesis").
- **L3 (Skills)**: The destination for crystallized plans.
- **L4 (Archives)**: The agent can read L4 to learn from past synthesis runs.

## 4. Operational Best Practices
- **Human Supervision**: Use the "STOP AGENT" button in the tab if the agent enters a planning loop.
- **Skill Reuse**: Check the L3 Skill Tree regularly. If a task is repeated often, ensure it has been correctly crystallized.
- **Context Loading**: For best results, ensure artifacts are fully "loaded" (Emerald status) before assigning complex agent tasks.

## 5. Security Constraints
- Agents cannot modify the `.env` or system `package.json`.
- All `askUser` requests are blocked unless an active user session is detected.
- Tool execution is rate-limited to prevent token exhaustion.

---

**Protocol: EdgeK-Alpha**
**Status: ACTIVE**
