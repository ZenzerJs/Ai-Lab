# BENCH-023: Raft-Lite Election and Log Replication Core

Repair only models.py, log.py, election.py, node.py, and cluster.py.
Python stdlib only; no network, sleeps, or paid services. The cluster is
fully synchronous and deterministic — no timers or randomness.

## API and invariants

- models: LogEntry(term, command); Role follower/candidate/leader;
  RequestVote, VoteReply, AppendEntries, AppendReply messages;
  ConsistencyError on safety violations.
- log.ReplicatedLog: 1-indexed entries; match(prev_index, prev_term);
  append_from(prev_index, entries, committed_index) truncates a
  conflicting suffix but NEVER a committed entry (ConsistencyError);
  up_to_date(last_index, last_term) compares term first, then index.
- election.grant_vote: stale term rejects; a newer term steps down and
  resets the vote; at most one grant per term (repeat grants to the same
  candidate are idempotent); the candidate log must be at least as
  up-to-date as the voter's.
- node.RaftNode: quorum = peers//2 + 1 (peers includes self);
  start_election bumps the term and votes for itself; on_vote_reply
  requires majority to become leader; append_command is leader-only;
  on_append_entries rejects stale terms and prev mismatches, updates
  commit_index to min(leader_commit, last_index); a leader advances
  commit_index only when an entry of the CURRENT term is replicated on a
  majority.
- cluster.Cluster: send/broadcast route messages and honor partition();
  elect(candidate_id) drives one election round; replicate(leader_id,
  command) appends and collects replies.

Visible tests are smoke coverage, not the complete specification.
