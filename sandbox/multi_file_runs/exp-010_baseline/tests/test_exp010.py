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


def test_markdown_parser_wikilink_anchors():
    parser = MarkdownParser()
    text = "See [[Architecture#Overview]] and [[Concepts]] and [[Guide#Setup-Step]]."
    links = parser.parse_wikilinks(text)
    assert len(links) == 3
    assert links[0] == ("Architecture", "Overview")
    assert links[1] == ("Concepts", "")
    assert links[2] == ("Guide", "Setup-Step")


def test_bm25_zero_division_resilience():
    ranker = BM25Ranker()
    score_zero = ranker.score(["term"], ["term"], {"term": 1}, 1, 0.0)
    assert score_zero >= 0.0

    score_normal = ranker.score(["python"], ["python", "rocks"], {"python": 1}, 1, 2.0)
    assert score_normal > 0.0


def test_inverted_index_deletion_cleanup():
    index = InvertedIndex()
    index.index_document("doc_1", ["apple", "banana"])
    index.index_document("doc_2", ["banana", "cherry"])

    assert "doc_1" in index.postings["banana"]
    assert "doc_1" in index.postings["apple"]

    index.delete_document("doc_1")

    assert "apple" not in index.postings
    assert "doc_1" not in index.postings["banana"]
    assert "doc_2" in index.postings["banana"]
    assert "doc_1" not in index.doc_lengths
