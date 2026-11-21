from cluster import Cluster
from node import RaftNode


def _cluster(n=3):
    ids = [f"n{i}" for i in range(n)]
    return Cluster([RaftNode(i, ids) for i in ids])


def test_election_smoke():
    cluster = _cluster(3)
    assert cluster.elect("n0") == "n0"


def test_replication_smoke():
    cluster = _cluster(3)
    cluster.elect("n0")
    cluster.replicate("n0", "set x=1")
    assert cluster.nodes["n0"].committed_commands() == ["set x=1"]
