"""Protected deterministic checks for BENCH-023."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import (AppendEntries, ConsistencyError, LogEntry,
                            RequestVote, Role)
        from node import RaftNode
        from cluster import Cluster

        def make_cluster(n=3):
            ids = [f"n{i}" for i in range(n)]
            nodes = [RaftNode(i, ids) for i in ids]
            return Cluster(nodes)

        def election_checks():
            cluster = make_cluster(3)
            assert cluster.elect("n0") == "n0"
            leader = cluster.nodes["n0"]
            assert leader.role is Role.LEADER
            assert leader.current_term == 1
            # One vote per term: a second candidate in term 1 is denied.
            req = RequestVote(1, "n1", 0, 0)
            assert not cluster.nodes["n2"].on_request_vote(req).granted
            # Same candidate re-asking is idempotent.
            req0 = RequestVote(1, "n0", 0, 0)
            assert cluster.nodes["n2"].on_request_vote(req0).granted
            # Stale terms rejected.
            assert not cluster.nodes["n0"].on_request_vote(
                RequestVote(0, "n1", 0, 0)).granted
            # A new term lets a fresh candidate win.
            cluster2 = make_cluster(3)
            cluster2.nodes["n0"].log.append_from(
                0, (LogEntry(1, "cmd"),))
            assert cluster2.elect("n1") == "n1"
            assert cluster2.nodes["n1"].current_term == 1

        def freshness_checks():
            cluster = make_cluster(3)
            stale = cluster.nodes["n0"]
            stale.log.append_from(0, (LogEntry(3, "a"), LogEntry(3, "b")))
            # Candidate with an OLDER log (lower term) must not win a vote.
            assert not stale.on_request_vote(
                RequestVote(4, "n1", 1, 1)).granted
            assert stale.current_term == 4   # stepped down, still no grant
            # Newer-term candidate log wins.
            assert cluster.nodes["n0"].on_request_vote(
                RequestVote(5, "n1", 5, 5)).granted
            # Higher index at equal term wins.
            other = RaftNode("n9", ["n9"])
            other.log.append_from(0, (LogEntry(2, "x"), LogEntry(2, "y")))
            assert other.log.up_to_date(3, 2)
            assert not other.log.up_to_date(1, 2)
            assert not other.log.up_to_date(3, 1)

        def replication_checks():
            cluster = make_cluster(3)
            cluster.elect("n0")
            leader = cluster.nodes["n0"]
            cluster.replicate("n0", "set x=1")
            assert leader.commit_index == 1
            for node in cluster.nodes.values():
                assert node.log.last_index == 1
            assert leader.committed_commands() == ["set x=1"]
            cluster.replicate("n0", "set y=2")
            assert leader.commit_index == 2
            # Followers learn the prior leader_commit on the next append.
            for nid, node in cluster.nodes.items():
                if nid != "n0":
                    assert node.committed_commands() == ["set x=1"]
            assert leader.committed_commands() == ["set x=1", "set y=2"]
            # Non-leader cannot append.
            rejected(ConsistencyError,
                     lambda: cluster.nodes["n1"].append_command("bad"))

        def safety_checks():
            cluster = make_cluster(5)
            ids = list(cluster.nodes)
            cluster.elect("n0")
            leader = cluster.nodes["n0"]
            # Partition: only n0+n1 reachable — minority; no commit advance.
            cluster.partition({"n2", "n3", "n4"})
            cluster.replicate("n0", "minority-write")
            assert leader.commit_index == 0
            cluster.heal()
            cluster.replicate("n0", "majority-write")
            assert leader.commit_index == 2
            # Stale-term append rejected.
            follower = cluster.nodes["n3"]
            resp = follower.on_append_entries(
                AppendEntries(leader.current_term - 1, "nX", 0, 0,
                              (LogEntry(1, "evil"),), 0))
            assert not resp.success
            # prev-term mismatch rejected.
            resp2 = follower.on_append_entries(
                AppendEntries(leader.current_term, "n0", 1, 99,
                              (LogEntry(1, "z"),), 0))
            assert not resp2.success
            # Committed entries are never truncated away.
            f2 = cluster.nodes["n4"]
            f2.commit_index = 2
            rejected(ConsistencyError, lambda: f2.log.append_from(
                0, (LogEntry(9, "overwrite"),), committed_index=2))
            assert f2.log.entries[0].command == "minority-write"

        def conflict_resolution_checks():
            cluster = make_cluster(3)
            cluster.elect("n0")
            cluster.replicate("n0", "a1")
            cluster.replicate("n0", "a2")
            # Diverge n1: a conflicting term-9 entry at index 3 gets
            # truncated by the leader's matching-prev append.
            n1 = cluster.nodes["n1"]
            n1.log.append_from(2, (LogEntry(9, "rogue"),))
            cluster.replicate("n0", "a3")
            assert n1.log.entries[1].command == "a2"
            assert n1.log.entries[2].command == "a3"   # rogue truncated
            assert n1.log.last_index == 3
            assert n1.committed_commands() == ["a1", "a2"]

        for check in (election_checks, freshness_checks,
                      replication_checks, safety_checks,
                      conflict_resolution_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: consensus_safety_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
