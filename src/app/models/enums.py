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
    SUB_WORKFLOW = "sub_workflow"
    EVENT = "event"


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
    SUSPENDED = "suspended"


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
    SEQUENTIAL = "sequential"
    RUNTIME_SELECTION = "runtime_selection"
    QUEUE = "queue"


class RoutingType(str, enum.Enum):
    CONDITIONAL = "conditional"
    PERFORMER_CHOSEN = "performer_chosen"
    BROADCAST = "broadcast"


class LifecycleState(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class PermissionLevel(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
