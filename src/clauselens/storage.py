"""SQLite persistence for analysis reports and user feedback (SQLAlchemy 2.x)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Integer, String, Text, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from clauselens.paths import DATA


class Base(DeclarativeBase):
    pass


class ReportRow(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_utc: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(String(32))
    overall_risk: Mapped[str] = mapped_column(String(8))
    payload: Mapped[str] = mapped_column(Text)  # JSON; clause text is PII-masked


class FeedbackRow(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(32), index=True)
    clause_index: Mapped[int] = mapped_column(Integer)
    labels: Mapped[str] = mapped_column(String(200), default="")
    risk: Mapped[str] = mapped_column(String(8), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_utc: Mapped[str] = mapped_column(String(32))


def report_title(report: dict[str, Any]) -> str:
    kind = report["doc_type"].replace("_", " ").title()
    return f"{kind} · {report['created_utc'][:10]}"


class Store:
    def __init__(self, url: str | None = None) -> None:
        url = url or os.environ.get("CLAUSELENS_DB")
        if url is None:
            path = DATA / "app" / "clauselens.db"
            path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{path}"
        elif "://" not in url:
            Path(url).parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{url}"
        kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        self.engine = create_engine(url, **kwargs)
        Base.metadata.create_all(self.engine)

    def save(self, report: dict[str, Any]) -> None:
        row = ReportRow(
            id=report["report_id"],
            created_utc=report["created_utc"],
            title=report_title(report),
            doc_type=report["doc_type"],
            overall_risk=report["summary"]["overall_risk"],
            payload=json.dumps(report, ensure_ascii=False),
        )
        with Session(self.engine) as session:
            session.merge(row)
            session.commit()

    def get(self, report_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            row = session.get(ReportRow, report_id)
            return json.loads(row.payload) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        stmt = select(ReportRow).order_by(ReportRow.created_utc.desc()).limit(limit)
        with Session(self.engine) as session:
            return [
                {"report_id": r.id, "created_utc": r.created_utc, "title": r.title,
                 "doc_type": r.doc_type, "overall_risk": r.overall_risk}
                for r in session.scalars(stmt)
            ]  # fmt: skip

    def delete(self, report_id: str) -> bool:
        with Session(self.engine) as session:
            existed = session.get(ReportRow, report_id) is not None
            session.execute(delete(FeedbackRow).where(FeedbackRow.report_id == report_id))
            session.execute(delete(ReportRow).where(ReportRow.id == report_id))
            session.commit()
            return existed

    def add_feedback(self, report_id: str, clause_index: int, labels: list[str] | None,
                     risk: str | None, note: str) -> None:  # fmt: skip
        with Session(self.engine) as session:
            session.add(
                FeedbackRow(
                    report_id=report_id,
                    clause_index=clause_index,
                    labels="|".join(labels or []),
                    risk=risk or "",
                    note=note,
                    created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                )
            )
            session.commit()

    def feedback(self, report_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(FeedbackRow).where(FeedbackRow.report_id == report_id).order_by(FeedbackRow.id)
        )
        with Session(self.engine) as session:
            return [
                {"clause_index": r.clause_index, "labels": r.labels.split("|") if r.labels else [],
                 "risk": r.risk or None, "note": r.note, "created_utc": r.created_utc}
                for r in session.scalars(stmt)
            ]  # fmt: skip
