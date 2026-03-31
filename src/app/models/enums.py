import enum


class ProcessState(str, enum.Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class ActivityType(str, enum.Enum):
    START = "start"
    END = "end"
    MANUAL = "manual"
    AUTO = "auto"


class FlowType(str, enum.Enum):
    NORMAL = "normal"
    REJECT = "reject"


class TriggerType(str, enum.Enum):
    AND_JOIN = "and_join"
    OR_JOIN = "or_join"


class WorkflowState(str, enum.Enum):
    DORMANT = "dormant"
    RUNNING = "running"
    HALTED = "halted"
    FAILED = "failed"
    FINISHED = "finished"


class WorkItemState(str, enum.Enum):
    ACQUIRED = "acquired"
    AVAILABLE = "available"
    DELEGATED = "delegated"
    COMPLETE = "complete"
    REJECTED = "rejected"


class ActivityState(str, enum.Enum):
    DORMANT = "dormant"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"
    ERROR = "error"


class PerformerType(str, enum.Enum):
    USER = "user"
    GROUP = "group"
    SUPERVISOR = "supervisor"
    ALIAS = "alias"
