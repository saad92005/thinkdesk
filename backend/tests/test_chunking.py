from app.documents.chunking import chunk_pages


def test_short_pages_produce_a_single_chunk():
    chunks = chunk_pages(["Just one short paragraph."], chunk_size=1000, chunk_overlap=100)
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert "short paragraph" in chunks[0].text


def test_long_text_is_split_and_indexed_sequentially():
    long_paragraph = "Sentence number filler. " * 200
    chunks = chunk_pages([long_paragraph], chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(len(c.text) <= 300 + 60 for c in chunks)  # allow small overlap slop


def test_chunk_carries_the_page_it_started_on():
    # A small chunk_size forces a flush between pages instead of merging
    # both pages' short paragraphs into one chunk tagged with page 1.
    pages = ["Page one content here.", "Page two content here, quite different."]
    chunks = chunk_pages(pages, chunk_size=10, chunk_overlap=0)
    pages_seen = {c.page_number for c in chunks}
    assert pages_seen == {1, 2}


def test_overlap_carries_trailing_text_into_the_next_chunk():
    long_paragraph = "Word{} ".format
    text = "".join(long_paragraph(i) for i in range(200))
    chunks = chunk_pages([text], chunk_size=200, chunk_overlap=50)
    assert len(chunks) >= 2
    tail_of_first = chunks[0].text[-20:]
    assert tail_of_first[:10] in chunks[1].text or tail_of_first[-10:] in chunks[1].text


def test_empty_pages_produce_no_chunks():
    assert chunk_pages(["", "   ", "\n\n"]) == []
