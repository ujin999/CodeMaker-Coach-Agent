from app.routers.auth import router as auth
from app.routers.problems import router as problems
from app.routers.submissions import router as submissions
from app.routers.hints import router as hints
from app.routers.community import router as community

__all__ = ["auth", "problems", "submissions", "hints", "community"]
