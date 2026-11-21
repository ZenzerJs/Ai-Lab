"""Raft-lite models: log entries, roles, and RPC messages."""
from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class ConsistencyError(RuntimeError):
    """Raised when a committed entry would be lost or rewritten."""


@dataclass(frozen=True)
class LogEntry:
    term: int
    command: str


@dataclass(frozen=True)
class RequestVote:
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass(frozen=True)
class VoteReply:
    term: int
    granted: bool
    voter_id: str


@dataclass(frozen=True)
class AppendEntries:
    term: int
    leader_id: str
    prev_index: int
    prev_term: int
    entries: tuple
    leader_commit: int


@dataclass(frozen=True)
class AppendReply:
    term: int
    success: bool
    follower_id: str
    match_index: int
