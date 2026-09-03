import os
import uuid
from datetime import datetime, timezone
import logging

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Date, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

logger = logging.getLogger(__name__)

Base = declarative_base()

class DecisionAction(enum.Enum):
    MONITORING_STARTED = "MONITORING_STARTED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    AUDIT_PASSED = "AUDIT_PASSED"

class TokenSnapshot(Base):
    __tablename__ = 'token_snapshots'

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_address = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    price_usd = Column(Float, nullable=True)
    liquidity_usd = Column(Float, nullable=True)
    market_cap_usd = Column(Float, nullable=True)
    
    raw_dexscreener_json = Column(JSONB, nullable=True)
    score_breakdown = Column(JSONB, nullable=True)

class DecisionLog(Base):
    __tablename__ = 'decision_log'

    decision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_address = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    action = Column(SQLEnum(DecisionAction, name="decision_action_enum"), nullable=False)
    reason = Column(String, nullable=True)
    bot_version = Column(String, nullable=False, default="1.2.0")

class PaperTrade(Base):
    __tablename__ = 'paper_trades'

    trade_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_address = Column(String, index=True, nullable=False)
    
    entry_time = Column(DateTime(timezone=True), nullable=False)
    entry_price = Column(Float, nullable=False)
    
    exit_time = Column(DateTime(timezone=True), nullable=True)
    exit_price = Column(Float, nullable=True)
    
    pnl_usd = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)

class DailyAggregate(Base):
    __tablename__ = 'daily_aggregates'

    date = Column(Date, primary_key=True)
    total_scanned = Column(Integer, default=0, nullable=False)
    total_passed = Column(Integer, default=0, nullable=False)
    total_rejected = Column(Integer, default=0, nullable=False)
    avg_pnl_pct = Column(Float, nullable=True)


class AnalyticsDBManager:
    def __init__(self, db_url: str = None):
        """
        Initializes the connection to the Azure Postgres Flexible Server.
        """
        self.db_url = db_url or os.environ.get("AZURE_POSTGRES_URL")
        
        if not self.db_url:
            logger.warning("[AzureDB] AZURE_POSTGRES_URL is not set. Analytics DB will not be connected.")
            self.engine = None
            self.SessionLocal = None
            return
            
        try:
            self.engine = create_engine(self.db_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("[AzureDB] Connected to Azure Postgres Flexible Server.")
        except Exception as e:
            logger.error(f"[AzureDB] Failed to connect to Azure DB: {e}")
            self.engine = None
            self.SessionLocal = None

    def init_schema(self):
        """
        Creates all tables based on the declarative base.
        """
        if not self.engine:
            logger.error("[AzureDB] Cannot init schema without a valid DB connection.")
            return
            
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("[AzureDB] Successfully initialized analytical schema on Azure Postgres.")
        except Exception as e:
            logger.error(f"[AzureDB] Failed to initialize schema: {e}")

    def insert_snapshot(self, token_address: str, price_usd: float, liquidity_usd: float, market_cap_usd: float, raw_json: dict, score_breakdown: dict):
        if not self.SessionLocal:
            return
        try:
            with self.SessionLocal() as session:
                snapshot = TokenSnapshot(
                    token_address=token_address,
                    price_usd=price_usd,
                    liquidity_usd=liquidity_usd,
                    market_cap_usd=market_cap_usd,
                    raw_dexscreener_json=raw_json,
                    score_breakdown=score_breakdown
                )
                session.add(snapshot)
                session.commit()
        except Exception as e:
            logger.error(f"[AzureDB] Failed to insert snapshot: {e}")

    def insert_decision(self, token_address: str, action: DecisionAction, reason: str = None):
        if not self.SessionLocal:
            return
        try:
            with self.SessionLocal() as session:
                decision = DecisionLog(
                    token_address=token_address,
                    action=action,
                    reason=reason
                )
                session.add(decision)
                session.commit()
        except Exception as e:
            logger.error(f"[AzureDB] Failed to insert decision: {e}")

    def upsert_daily_aggregate(self, date_obj, scanned: int, passed: int, rejected: int, avg_pnl: float):
        if not self.SessionLocal:
            return
        try:
            with self.SessionLocal() as session:
                agg = session.query(DailyAggregate).filter_by(date=date_obj).first()
                if not agg:
                    agg = DailyAggregate(date=date_obj)
                    session.add(agg)
                agg.total_scanned = scanned
                agg.total_passed = passed
                agg.total_rejected = rejected
                agg.avg_pnl_pct = avg_pnl
                session.commit()
        except Exception as e:
            logger.error(f"[AzureDB] Failed to upsert daily aggregate: {e}")

    def insert_paper_trade(self, token_address: str, entry_time, entry_price: float, exit_time=None, exit_price=None, pnl_usd=None, pnl_pct=None):
        if not self.SessionLocal:
            return
        try:
            with self.SessionLocal() as session:
                trade = PaperTrade(
                    token_address=token_address,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=exit_time,
                    exit_price=exit_price,
                    pnl_usd=pnl_usd,
                    pnl_pct=pnl_pct
                )
                session.add(trade)
                session.commit()
        except Exception as e:
            logger.error(f"[AzureDB] Failed to insert paper trade: {e}")
