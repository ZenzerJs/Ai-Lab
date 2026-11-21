"""Deterministic cluster: synchronous message routing between nodes."""
from models import (AppendEntries, AppendReply, RequestVote, Role,
                    VoteReply)


class Cluster:
    def __init__(self, nodes):
        self.nodes = {n.node_id: n for n in nodes}
        self.blocked = set()    # node_ids cut off from the network

    def send(self, target_id, message):
        if target_id in self.blocked:
            return None
        node = self.nodes[target_id]
        if isinstance(message, RequestVote):
            return node.on_request_vote(message)
        if isinstance(message, AppendEntries):
            return node.on_append_entries(message)
        raise ValueError(f"unknown message {type(message).__name__}")

    def broadcast(self, sender_id, messages):
        if sender_id in self.blocked:
            return []
        replies = []
        for target_id, msg in zip(
                [p for p in self.nodes if p != sender_id], messages):
            reply = self.send(target_id, msg)
            if reply is not None:
                replies.append(reply)
        return replies

    def elect(self, candidate_id):
        """Run one election round; returns the leader's id or None."""
        candidate = self.nodes[candidate_id]
        replies = self.broadcast(
            candidate_id, candidate.start_election())
        for reply in replies:
            if isinstance(reply, VoteReply):
                candidate.on_vote_reply(reply)
        return candidate_id if candidate.role is Role.LEADER else None

    def replicate(self, leader_id, command):
        """Append a command on the leader and deliver to followers,
        retrying with a lower prev_index until the logs line up."""
        leader = self.nodes[leader_id]
        msgs = leader.append_command(command)
        commit_at_send = leader.commit_index
        if leader_id in self.blocked:
            return commit_at_send
        for target_id, msg in zip(
                [p for p in self.nodes if p != leader_id], msgs):
            prev_index = msg.prev_index
            while prev_index >= -1:
                sync = leader.sync_entries(prev_index, commit_at_send)
                reply = self.send(target_id, sync)
                if reply is None:
                    break
                if isinstance(reply, AppendReply):
                    leader.on_append_reply(reply)
                    # A higher-term reply demotes the leader; stop
                    # replicating — a follower must not send appends.
                    if leader.role is not Role.LEADER:
                        return leader.commit_index
                    if reply.success:
                        break
                prev_index -= 1
        return leader.commit_index

    def partition(self, node_ids):
        self.blocked = set(node_ids)

    def heal(self):
        self.blocked = set()
