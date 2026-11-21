"""RaftNode: term fencing, elections, replication, majority commit."""
from election import grant_vote
from log import ReplicatedLog
from models import (AppendEntries, AppendReply, ConsistencyError,
                    LogEntry, RequestVote, Role)


class RaftNode:
    def __init__(self, node_id, peers):
        self.node_id = node_id
        self.peers = list(peers)
        self.role = Role.FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.log = ReplicatedLog()
        self.commit_index = 0
        self._votes = set()
        self.match_index = {}      # leader-only: peer -> replicated index

    @property
    def quorum(self):
        return len(self.peers) // 2 + 1   # peers includes self

    def on_request_vote(self, request):
        return grant_vote(self, request)

    def start_election(self):
        """Become a candidate: bump term, vote for self, emit RequestVotes."""
        self.current_term += 1
        self.role = Role.CANDIDATE
        self.voted_for = self.node_id
        self._votes = {self.node_id}
        self.match_index = {}
        return [
            RequestVote(self.current_term, self.node_id,
                        self.log.last_index, self.log.last_term)
            for _ in self.peers if _ != self.node_id
        ]

    def on_vote_reply(self, reply):
        """Count votes; majority makes us leader."""
        if reply.term > self.current_term:
            self.current_term = reply.term
            self.role = Role.FOLLOWER
            self.voted_for = None
            return False
        if self.role is not Role.CANDIDATE or not reply.granted:
            return False
        self._votes.add(reply.voter_id)
        if len(self._votes) >= self.quorum:
            self.role = Role.LEADER
            self.match_index = {p: 0 for p in self.peers if p != self.node_id}
            self.match_index[self.node_id] = self.log.last_index
            return True
        return False

    def append_command(self, command):
        """Leader-only: append locally and emit AppendEntries per follower."""
        if self.role is not Role.LEADER:
            raise ConsistencyError("only a leader appends")
        entry = LogEntry(self.current_term, command)
        self.log.append_from(self.log.last_index, (entry,))
        self.match_index[self.node_id] = self.log.last_index
        prev_index = self.log.last_index - 1
        prev_term = self.log.term_at(prev_index)
        return [
            AppendEntries(self.current_term, self.node_id,
                          prev_index, prev_term, (entry,),
                          self.commit_index)
            for _ in self.peers if _ != self.node_id
        ]

    def sync_entries(self, prev_index, leader_commit=None):
        """Rebuild an AppendEntries carrying every entry after
        prev_index — used to resync followers whose logs diverged."""
        if leader_commit is None:
            leader_commit = self.commit_index
        entries = tuple(self.log.entries[max(prev_index, 0):])
        return AppendEntries(self.current_term, self.node_id,
                             prev_index, self.log.term_at(prev_index),
                             entries, leader_commit)

    def on_append_entries(self, msg):
        """Accept an append when the leader's term is fresh and prev matches."""
        if msg.term < self.current_term:
            return AppendReply(self.current_term, False,
                               self.node_id, self.log.last_index)
        if msg.term > self.current_term:
            self.current_term = msg.term
            self.voted_for = None
        self.role = Role.FOLLOWER
        if not self.log.match(msg.prev_index, msg.prev_term):
            return AppendReply(self.current_term, False,
                               self.node_id, self.log.last_index)
        self.log.append_from(msg.prev_index, msg.entries,
                             committed_index=self.commit_index)
        self.commit_index = min(msg.leader_commit, self.log.last_index)
        return AppendReply(self.current_term, True,
                           self.node_id, self.log.last_index)

    def on_append_reply(self, reply):
        """Leader tracks match indexes; a majority match on a current-term
        entry advances commit_index."""
        if self.role is not Role.LEADER or not reply.success:
            return False
        self.match_index[reply.follower_id] = reply.match_index
        for index in range(self.log.last_index, self.commit_index, -1):
            replicated = sum(
                1 for idx in self.match_index.values() if idx >= index)
            if replicated >= self.quorum \
                    and self.log.at(index).term == self.current_term:
                self.commit_index = index
                return True
        return False

    def committed_commands(self):
        return [e.command for e in self.log.entries[:self.commit_index]]
