# LangChain tracked-ingestion example

This example shows where VectorLedger fits into an existing LangChain ingestion flow. It does not replace the splitter, embedding model, or vector store.

The important contract is that every chunk receives the same `tenant_id`, stable `document_id`, and `document_version`. After the vector store returns record IDs, the pipeline registers those locations with VectorLedger.

```bash
pip install vectorledger langchain-core langchain-text-splitters
python examples/langchain/tracked_ingestion.py
```

Replace the illustrative `add_to_your_vector_store` function with the vector store already used by your application.
