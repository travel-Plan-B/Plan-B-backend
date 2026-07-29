from app.core.database import Base, engine
from app.models.place import Place  # noqa: F401

Base.metadata.create_all(bind=engine)
print("테이블 생성 완료")
