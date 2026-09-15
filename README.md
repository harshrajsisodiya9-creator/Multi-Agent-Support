The product is a customer support chatbot for my client's ecommerce store. It's chat widget is embedded directly into the storefront, while the backend that powers it runs separately, hosted on Cloud Run. It answers store policy questions (returns, shipping, etc.) and looks up order status for logged-in customers, including combined queries like "can I return order #1234" where it checks both the relevant policy and the order details before responding. It also keeps context across a conversation, so customers can ask follow-up questions without repeating themselves.

High Level Architecture
![High Level Architecture](chatbot_request_flow.svg)

Frontend (Shopify theme app extension)
The chat widget is built as a Shopify theme app extension client-side JavaScript embedded directly into the storefront theme. It renders the chat UI and handles user input. For logged-in customers, it passes their logged_in_customer_id as a URL parameter to the Shopify App Proxy, which the backend uses to identify the customer and key their conversation history. Guests can still use the widget, but without persisted history across messages.

App Proxy
Shopify's App Proxy sits between the storefront widget and the FastAPI backend. It forwards the widget's requests including the logged_in_customer_id to the backend hosted on Cloud Run. Since requests are routed through Shopify's own domain rather than calling Cloud Run directly from the browser, it also acts as a CORS bridge, meaning the backend doesn't need to configure CORS itself.

Backend (FastAPI on Cloud Run)
The backend is a FastAPI application deployed on Cloud Run. It's async end-to-end, any CPU-bound work is offloaded to a worker thread so the event loop stays unblocked. The LangGraph workflow is compiled lazily on the first incoming request and then reused for all subsequent requests.

Router agent
The entry point of the graph. It uses an LLM (via ChatGroq) with structured output to classify each incoming message and decide which path to take: a store-policy question, an order-related question, both (for combined queries like "can I return order #1234"), or out-of-scope.

RAG node(policy questions)
Handles store-policy questions using retrieval-augmented generation. Store policy documents are embedded(local ) into a local vector store (Chroma/FAISS), and relevant chunks are retrieved and passed to the LLM to generate a grounded answer.

Order Node
Handles order-related questions. It calls Shopify's GraphQL Admin API asynchronously to fetch order details using email address and order number provided by the customer in the query.
