"""Test suite for EXP-010 Knowledge Graph Engine."""
from kg_engine.bm25 import BM25Ranker
from kg_engine.exporter import GraphExporter
from kg_engine.graph import KnowledgeGraph
from kg_engine.indexer import InvertedIndex
from kg_engine.parser import MarkdownParser


def test_knowledge_graph_bidirectional_centrality():
    kg = KnowledgeGraph()
    kg.add_edge("note_a", "note_b")
    kg.add_edge("note_c", "note_b")

    cent = kg.degree_centrality("note_b")
    assert cent["in_degree"] == 2
    assert cent["out_degree"] == 0


def test_cytoscape_exporter_format():
    kg = KnowledgeGraph()
    kg.add_edge("concept_x", "concept_y")
    data = GraphExporter.to_cytoscape(kg)

    assert "elements" in data
    assert len(data["elements"]) == 3  # 2 nodes + 1 edge


def test_markdown_parser_frontmatter():
    doc = "---\ntitle: Test Note\nstatus: active\n---\n\n# Hello world"
    parser = MarkdownParser()
    meta = parser.extract_frontmatter(doc)
    assert meta["title"] == "Test Note"
    assert meta["status"] == "active"


def test_wikilink_anchor_parsing():
    parser = MarkdownParser()
    content = "See [[Architecture#Overview]] and normal [[Design]] notes."
    links = parser.parse_wikilinks(content)
    assert len(links) == 2
    assert links[0] == ("Architecture", "Overview")
    assert links[1] == ("Design", "")


def test_bm25_zero_division_protection():
    ranker = BM25Ranker()
    # Edge case: avg_doc_len = 0.0 or doc_len == avg_doc_len
    score = ranker.score(
        query_terms=["graph"],
        doc_terms=["graph", "notes"],
        doc_freqs={"graph": 1},
        total_docs=1,
        avg_doc_len=0.0,
    )
    assert isinstance(score, float)
    assert score > 0.0


def test_inverted_index_deletion_cleanup():
    idx = InvertedIndex()
    idx.index_document("doc1", ["python", "ast"])
    idx.index_document("doc2", ["python", "types"])

    assert "doc1" in idx.search("python")
    idx.delete_document("doc1")
    assert "doc1" not in idx.search("python")
    assert "doc1" not in idx.search("ast")
    assert "doc2" in idx.search("python")
