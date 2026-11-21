"""Cluster: synchronous message routing."""
from models import AppendEntries, AppendReply, RequestVote, VoteReply


class Cluster:
    def __init__(self, nodes):
        self.nodes = {n.node_id: n for n in nodes}
        self.blocked = set()

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
        replies = []
        for target_id, msg in zip(
                [p for p in self.nodes if p != sender_id], messages):
            reply = self.send(target_id, msg)
            if reply is not None:
                replies.append(reply)
        return replies

    def elect(self, candidate_id):
        candidate = self.nodes[candidate_id]
        replies = self.broadcast(candidate_id, candidate.start_election())
        for reply in replies:
            if isinstance(reply, VoteReply):
                if candidate.on_vote_reply(reply):
                    return candidate_id
        return None

    def replicate(self, leader_id, command):
        leader = self.nodes[leader_id]
        replies = self.broadcast(leader_id, leader.append_command(command))
        for reply in replies:
            if isinstance(reply, AppendReply):
                leader.on_append_reply(reply)
        return leader.commit_index

    def partition(self, node_ids):
        self.blocked = set(node_ids)

    def heal(self):
        self.blocked = set()
