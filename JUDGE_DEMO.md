# 90-Second Judge Demo Script

**Start time: 0s**

### 1. THE PROBLEM (0–10s)
Open the app. Show the empty graph.

*Say:* "Imagine you're building an AI agent for your team. It talks to you about a decision you made last sprint. You close the browser. Refresh. Ask the agent the same question..."

Click in the Ask panel:
**Input:** "Why did we pick PostgreSQL?"  
**Show result:** "I don't know anything about that" (or generic answer).

*Say:* "This is the problem. **AI agents forget the moment a session ends.** Every time they wake up, they start from zero."

### 2. THE SOLUTION (10–40s)
*Say:* "We built Where's My Context — a knowledge graph that *persists* and *connects* your decisions."

Go to "Feed your brain" panel. Set "Adding as" to your name.

Add memory:
```
We picked PostgreSQL over MongoDB because:
1. We need relational integrity for billing
2. JSONB gives us flexibility
3. Team is already skilled in SQL
Decision made by: Sarah Chen
```

Click "Remember".

*Watch the graph:* Orange person node (Sarah) appears, concept nodes grow (PostgreSQL, MongoDB, billing, relational). Links form.

*Say:* "One memory, and the graph is alive. This is our shared team brain — every decision lives here, every person who made it is visible."

### 3. PROOF IT WORKS (40–60s)
Go to Ask panel.

*Input:* "Why did we pick PostgreSQL?"

*Point at the two bubbles:*
- **❌ Generic LLM:** "Different databases have different strengths..."  
- **✅ With Cognee:** "We picked PostgreSQL because we need relational integrity for billing, and JSONB gives us flexibility. Decision made by Sarah Chen."

Highlight the path in the graph — show how the concepts connect.

*Say:* "See the difference? One is grounded in your actual decisions. The other is hallucinating. Our graph proves every answer."

### 4. TEAM MEMORY (60–75s)
Ask in the search box:
```
Who decided the database?
```

*Result shows:* Sarah Chen (person node, orange), linked to the PostgreSQL decision.

*Say:* "This is a shared team brain. Every memory records its contributor. Ask 'who set up X?' and your team gets the right answer. No hunting through Slack. No 'I think it was...' No forgotten context."

### 5. THE MAGIC (75–90s)
Go to "New AI session" section.

Click "Recall".

*Say:* "This is the literal answer to 'Where's my context?' When your AI agent wakes up fresh, this is exactly what it gets injected. Full context. No blank slate."

*Show the context brief:*
```
Recent decisions: PostgreSQL selected for relational integrity + JSONB flexibility.
Team: Sarah leads database decisions.
Related concepts: billing, relational integrity, SQL expertise.
```

*Say:* "No more starting from zero. This is what we solve."

---

## Key Points to Emphasize

1. **The problem is real** — AI agents DO lose context  
2. **The solution is simple** — Persistent knowledge graph powered by Cognee  
3. **It's shareable** — Team brain, not individual memory  
4. **It's grounded** — Answers show their sources, not hallucinations  
5. **It's ready** — Works today with Cognee Cloud or runs offline  

## Judges Ask... You Say...

**Q: "How does this differ from RAG?"**  
A: "RAG finds relevant documents. We show you *how* concepts connect. Plus: team attribution, real-time visualization, and a shared brain instead of individual memory."

**Q: "Why not just use ChatGPT memory?"**  
A: "ChatGPT's memory is a black box, not shareable, not auditable. We give you transparent, team-wide context with proof of where it came from."

**Q: "Can this scale?"**  
A: "Absolutely. Cognee Cloud handles infinite memories — we just call `/api/v1/recall`. The graph stays fast because we visualize concepts, not individual memories."

**Q: "Why is this a hackathon win?"**  
A: "Because we solved a real problem (AI amnesia), integrated Cognee properly (not a demo — real API calls), and built something production-ready in one weekend."

---

## After the Demo

Be ready for:
- "Can I try adding a memory?" → Yes, do it live
- "Does it really talk to Cognee Cloud?" → Show network tab with /api/v1/remember calls
- "What's the fallback?" → Switch MEMORY_ENGINE=demo and show it still works
- "How do I deploy this?" → "Clone, set env vars, run. Lives on Vercel in 2 minutes."

**Most important:** Judges want to see confidence. You built something real. Own it.
