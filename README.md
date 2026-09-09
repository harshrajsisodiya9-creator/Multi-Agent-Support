This intentionally covers the base only: no Shopify connection, authentication,
conversation memory, observability/evaluations, or production error strategy yet.

Upload and index an FAQ document. Each question must begin at the start of a
line with `Q:`. Its answer is kept in the same retrieval chunk, up to the next
`Q:` line. For example:

```text
Q: What is your return policy?
A: Returns are accepted within 30 days of delivery.

Q: How long does shipping take?
A: Standard shipping takes 3–5 business days.
```

Upload and index the FAQ file:

```bash
curl -X POST http://localhost:8000/documents -F "file=@./company-faq.txt"
```

`POST /documents` can be called repeatedly. Uploading a file with the same name
replaces that document's prior indexed chunks; other documents remain in the
knowledge base.


Next in line
- Add structured error handling, authentication, logging, and rate limits.
- Add curated questions and retrieval/answer-quality evaluations.

Realizing something now that instead of OrderNode i could edit to something customer info which could call tools to get the relvant info, for now since the client doesnt need anything else related to customer except orders keep it as is

Final call to llm inside the response node can be skipped if only retrieval is required since the RAG node does use llm to generate response

Mistake: Naming convention of RAG.py is wrong since we are only retrieving using that node and not generating(not in that step)

Latency Optimization: While tracing requests with LangSmith, I noticed that the final response agent was taking a significant amount of time. After investigating the data being passed from the OrderNode, I found that it was returning the raw Shopify order response instead of a clean, structured representation of the order information. I changed the OrderNode to extract only the relevant fields, such as fulfillment status, financial status, items, total, and tracking information, before passing the data to the final agent. This reduced the amount of unnecessary context the LLM had to process and brought the end-to-end latency for the same request down from 2.03s to 1.74s.