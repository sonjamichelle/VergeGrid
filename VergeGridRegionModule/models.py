
# ================================================================
# VergeGrid SQLAlchemy ORM Models (Dedicated 'vergegrid' schema)
# ================================================================
from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean, Enum, ForeignKey, TIMESTAMP
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class NodeStatus(enum.Enum):
    active = 'active'
    inactive = 'inactive'
    quarantined = 'quarantined'

class RegionState(enum.Enum):
    active = 'active'
    stopped = 'stopped'
    deleted = 'deleted'

class UserRole(enum.Enum):
    admin = 'admin'
    operator = 'operator'
    viewer = 'viewer'


class VGNode(Base):
    __tablename__ = 'vg_nodes'
    __table_args__ = {'schema': 'vergegrid'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_uuid = Column(String(36), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    api_key = Column(String(128), nullable=False)
    endpoint_url = Column(String(255))
    status = Column(Enum(NodeStatus), default=NodeStatus.inactive)
    created_at = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')

    trust_scores = relationship('VGTrustScore', back_populates='node')
    keys = relationship('VGKey', back_populates='node')


class VGRegion(Base):
    __tablename__ = 'vg_regions'
    __table_args__ = {'schema': 'vergegrid'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    region_uuid = Column(String(36), unique=True, nullable=False)
    sim_uuid = Column(String(36), nullable=False)
    name = Column(String(128))
    template_version = Column(String(32))
    state = Column(Enum(RegionState), default=RegionState.active)
    created_at = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')


class VGTrustScore(Base):
    __tablename__ = 'vg_trust_scores'
    __table_args__ = {'schema': 'vergegrid'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_uuid = Column(String(36), ForeignKey('vergegrid.vg_nodes.node_uuid'), nullable=False)
    trust_score = Column(Float, default=1.0)
    last_update = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')

    node = relationship('VGNode', back_populates='trust_scores')


class VGKey(Base):
    __tablename__ = 'vg_keys'
    __table_args__ = {'schema': 'vergegrid'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_uuid = Column(String(36), ForeignKey('vergegrid.vg_nodes.node_uuid'), nullable=False)
    public_key = Column(Text, nullable=False)
    key_hash = Column(String(64), nullable=False)
    rotation_date = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')
    revoked = Column(Boolean, default=False)

    node = relationship('VGNode', back_populates='keys')


class VGUserRole(Base):
    __tablename__ = 'vg_user_roles'
    __table_args__ = {'schema': 'vergegrid'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False, unique=True)
    role = Column(Enum(UserRole), default=UserRole.viewer)
    created_at = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')


class VGAuditLog(Base):
    __tablename__ = 'vg_audit_log'
    __table_args__ = {'schema': 'vergegrid'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(128))
    message = Column(Text)
    actor_id = Column(String(36))
    timestamp = Column(TIMESTAMP, default='CURRENT_TIMESTAMP')
    encrypted = Column(Boolean, default=False)
