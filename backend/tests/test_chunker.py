import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.documents.chunker import chunk_text

valid_params = st.integers(min_value=1, max_value=200).flatmap(
    lambda size: st.tuples(st.just(size), st.integers(min_value=0, max_value=size - 1))
)


@given(text=st.text(), params=valid_params)
@settings(deadline=None)
def test_indexes_are_sequential(text, params):
    chunk_size, chunk_overlap = params
    chunks = chunk_text(text, document_id=1, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    assert [c.index for c in chunks] == list(range(len(chunks)))


@given(text=st.text(), params=valid_params)
@settings(deadline=None)
def test_chunks_are_never_blank(text, params):
    chunk_size, chunk_overlap = params
    chunks = chunk_text(text, document_id=1, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    assert all(c.text.strip() for c in chunks)


@given(text=st.text(), params=valid_params)
@settings(deadline=None)
def test_chunk_never_exceeds_chunk_size(text, params):
    chunk_size, chunk_overlap = params
    chunks = chunk_text(text, document_id=1, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    assert all(len(c.text) <= chunk_size for c in chunks)


@given(text=st.text(min_size=1), params=valid_params)
@settings(deadline=None)
def test_no_content_is_lost(text, params):
    chunk_size, chunk_overlap = params
    chunks = chunk_text(text, document_id=1, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    joined = "".join(c.text for c in chunks)
    for character in text:
        if not character.isspace():
            assert character in joined


@given(text=st.text(), params=valid_params)
@settings(deadline=None)
def test_every_chunk_belongs_to_the_document(text, params):
    chunk_size, chunk_overlap = params
    chunks = chunk_text(text, document_id=42, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    assert all(c.document_id == 42 for c in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(10, 10), (10, 20), (0, 0), (-1, 0), (10, -1)],
)
def test_invalid_params_raise_instead_of_hanging(chunk_size, chunk_overlap):
    with pytest.raises(ValueError):
        chunk_text("text", document_id=1, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
