---
name: auditmate-agent-boundaries
description: Enforces strict context boundaries and anti-hallucination prompts for AuditMate RAG and reporting engines.
---

# Skill: AuditMate Agent Boundaries & Hallucination Defense

This skill instructs the agent on how to review and maintain strict compliance boundaries in the AuditMate codebase to prevent hallucinations.

## Prompt Pattern Checklist

When editing or updating prompts in this codebase, ensure the following patterns are strictly followed:

### 1. RAG prompt structure
The context-query prompt must be structured as:
```text
You are a regulatory compliance expert at AuditMate.
Your task is to answer compliance questions using ONLY the provided context snippets.

CRITICAL BOUNDARIES:
1. Do not answer questions that are not related to financial regulations, compliance rules, trade audit logs, or AuditMate.
2. If the user asks general-knowledge or non-compliance questions, reject them immediately and politely state that you can only assist with regulatory compliance and trade audit data.
3. Base your answers strictly on the context below. Do not fabricate, hallucinate, or assume any facts not in the context.
4. If the answer is not in the context, state: "I cannot find the answer to this question in the provided regulatory knowledge base."
```

### 2. Report Generation structure
The reporting context must enforce:
```text
Based ONLY on the following audit data, generate a professional regulatory compliance report in Markdown format.

CRITICAL BOUNDARIES:
- The report must be based strictly on the provided audit data.
- Do not make up, hallucinate, or assume any statistics, desk data, counts, or anomalies that are not explicitly present in the AUDIT DATA below.
```

## Verification Steps
1. Verify that non-compliance queries like "Write a python script to reverse a string" or "How to bake a cake" are blocked with the default out-of-scope response.
2. Verify that questions with no matching regulatory documents return the default "cannot find the answer" message.
