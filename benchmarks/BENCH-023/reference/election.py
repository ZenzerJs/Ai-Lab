"""Election rules: one vote per term, freshness-gated grants."""
from models import VoteReply


def grant_vote(node, request):
    """Decide a RequestVote per Raft rules:

    - stale term -> reject
    - newer term -> step down first, then judge
    - at most one grant per term (repeat grants to the same candidate ok)
    - candidate log must be at least as up-to-date as ours
    """
    if request.term < node.current_term:
        return VoteReply(node.current_term, False, node.node_id)
    if request.term > node.current_term:
        node.current_term = request.term
        node.voted_for = None
        node.role = node.role.FOLLOWER
    up_to_date = node.log.up_to_date(
        request.last_log_index, request.last_log_term)
    granted = up_to_date and (
        node.voted_for is None or node.voted_for == request.candidate_id)
    if granted:
        node.voted_for = request.candidate_id
    return VoteReply(node.current_term, granted, node.node_id)
