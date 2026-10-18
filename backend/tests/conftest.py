import os
import tempfile

# Configure BEFORE the app is imported: fake embeddings, mock LLM, temp data dir.
os.environ["EMBEDDINGS_PROVIDER"] = "fake"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["VECTOR_STORE"] = "faiss"
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="docmind_test_")
