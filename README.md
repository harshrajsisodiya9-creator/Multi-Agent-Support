This intentionally covers the base only(for now): no connection with ui, authentication,
conversation memory, observability/evaluations, or production error strategy yet.

Upload and index a document:

```bash
curl -X POST http://localhost:8000/documents -F "file=@./company-handbook.pdf"
```

`POST /documents` can be called repeatedly. Uploading a file with the same name
replaces that document's prior indexed chunks; other documents remain in the
knowledge base.


Next in line
- Connect with clients ui for testing
- Containerize and deploy on Cloud, have a working demo for client
- Add curated questions and retrieval/answer-quality evaluations.
- Conversation memory addition
- Add structured error handling, authentication, logging, and rate limits.
