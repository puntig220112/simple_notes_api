import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from uuid import uuid4

from IVahit.model._model import Base, Note, Tag
from IVahit.crud import Crud, CrudElementNotFoundException
from IVahit.main import app  # oder dein FastAPI-App-Modul


# -------- Test Setup --------
@pytest.fixture(scope="function")
def in_memory_engine():
    """Erzeugt eine frische SQLite-DB im Speicher."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def crud(in_memory_engine):
    return Crud(in_memory_engine)


@pytest.fixture(scope="function")
def client(monkeypatch, in_memory_engine):
    """Patcht get_prod_endinge() für FastAPI, damit Tests die In-Memory-DB verwenden."""
    from IVahit import engines

    monkeypatch.setattr(engines, "get_prod_endinge", lambda: in_memory_engine)
    return TestClient(app)


# -------- Unit Tests für Crud.DeleteNote --------
def test_delete_note_success(crud: Crud):
    # Arrange
    with Session(crud._engine) as session:
        note = Note(note="Testnote")
        tag = Tag(tag="tag1", note=note)
        session.add(note)
        session.add(tag)
        session.commit()
        note_id = note.id

    # Act
    result = crud.DeleteNote(note_id)

    # Assert
    assert "deleted successfully" in result["message"]

    # Prüfen, dass sie wirklich gelöscht wurde
    with Session(crud._engine) as session:
        assert session.get(Note, note_id) is None
        assert session.query(Tag).count() == 0


def test_delete_note_not_found(crud: Crud):
    random_id = uuid4()
    with pytest.raises(CrudElementNotFoundException):
        crud.DeleteNote(random_id)


# -------- Integration Tests für FastAPI-Endpunkt --------
def test_api_delete_note_success(client: TestClient, in_memory_engine):
    # Arrange
    with Session(in_memory_engine) as session:
        note = Note(note="API Note")
        session.add(note)
        session.commit()
        note_id = note.id

    # Act
    response = client.delete(f"/note/{note_id}")

    # Assert
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Prüfen, dass DB leer ist
    with Session(in_memory_engine) as session:
        assert session.get(Note, note_id) is None


def test_api_delete_note_not_found(client: TestClient):
    # Act
    response = client.delete(f"/note/{uuid4()}")

    # Assert
    assert response.status_code == 404
    assert "No Note with id" in response.json()["detail"]
