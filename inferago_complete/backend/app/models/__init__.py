# Import in dependency order — SQLAlchemy needs FK targets registered first.
# See: https://docs.sqlalchemy.org/en/20/faq/orm_configuration.html#how-do-i-configure-self-referential-relationships-and-late-mappers
from app.models.user import User          # no deps
from app.models.workflow import Workflow  # → users
from app.models.api_key import ApiKey     # → users
from app.models.policy import Policy      # → users
from app.models.alert import Alert         # → users, workflows
from app.models.audit_log import AuditLog # → users
from app.models.run import Run, TokenUsage # → users, workflows
from app.models.rag import RAGMetrics      # → users, workflows, runs
# security_finding depends on users, workflows, runs, policies — import last
from app.models.security_finding import SecurityFinding
