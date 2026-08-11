from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class Place(Base):
    __tablename__ = "places"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    source = Column(String(20), nullable=False)  # tourapi | google
    source_id = Column(String(100), nullable=False)

    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)
    category_tag = Column(String(50), nullable=False)
    is_indoor = Column(Boolean, nullable=True)

    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    region = Column(String(50), nullable=True)

    image_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    rating = Column(Numeric(2, 1), nullable=True)
    user_rating_count = Column(Integer, nullable=True)

    operating_hours = Column(Text, nullable=True)
    parking_available = Column(Boolean, nullable=True)
    parking_status = Column(String(20), nullable=True)

    raw_category_source = Column(String(100), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_place_source_id"),
        Index("ix_place_lat_lng", "lat", "lng"),
        Index("ix_place_category_tag", "category_tag"),
        Index("ix_place_region", "region"),
    )
