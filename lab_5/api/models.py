import os

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(os.environ["DATABASE_URL"])
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)


class Operation(Base):
    __tablename__ = "operations"
    operation_id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String)
    customer_id: Mapped[str] = mapped_column(String)
    store_id: Mapped[str] = mapped_column(String)
    check_number: Mapped[str] = mapped_column(String)
    amount = mapped_column(Numeric(12, 2), nullable=True)  # Decimal
    points_delta: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)  # applied / rejected
    reject_reason = mapped_column(String, nullable=True)
    occurred_at = mapped_column(DateTime(timezone=True))
    processed_at = mapped_column(DateTime(timezone=True))
