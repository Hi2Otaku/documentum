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


class PerformerType(str, enum.Enum):
    USER = "user"
    GROUP = "group"
    SUPERVISOR = "supervisor"
    ALIAS = "alias"
