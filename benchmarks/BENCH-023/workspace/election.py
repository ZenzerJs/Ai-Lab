"""Election rules."""
from models import VoteReply


def grant_vote(node, request):
    if request.term < node.current_term:
        return VoteReply(node.current_term, False, node.node_id)
    if request.term > node.current_term:
        node.current_term = request.term
        node.voted_for = None
        node.role = node.role.FOLLOWER
    # Grant whenever we can: freshness and double-voting unchecked.
    node.voted_for = request.candidate_id
    return VoteReply(node.current_term, True, node.node_id)
