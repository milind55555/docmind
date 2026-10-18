from fastapi.testclient import TestClient

from app.main import app


def test_upload_chat_delete_flow():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"

        r = client.post(
            "/api/documents",
            files={"file": ("devops.txt", b"Terraform provisions infrastructure as code on AWS.", "text/plain")},
        )
        assert r.status_code == 201
        doc_id = r.json()["id"]
        assert len(client.get("/api/documents").json()) == 1

        with client.stream("POST", "/api/chat", json={"question": "What does Terraform do?"}) as resp:
            body = "".join(resp.iter_text())
        assert "event: sources" in body and "event: token" in body and "event: done" in body
        assert "Terraform" in body

        assert client.delete(f"/api/documents/{doc_id}").status_code == 204
        assert client.get("/api/documents").json() == []


def test_bad_file_type_returns_422():
    with TestClient(app) as client:
        r = client.post("/api/documents", files={"file": ("a.exe", b"x", "application/octet-stream")})
        assert r.status_code == 422
