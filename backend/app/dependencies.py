"""Demo-simplified auth: role comes from an `X-User-Role` header instead of a
full login/session system (out of scope for this build). This is enough to
demonstrate the RBAC concept the compliance requirements call for - every PHI
read still goes through get_current_user + is audit-logged (see audit.py) -
without building out real authentication, which would need its own project.
In production this header would be replaced by a verified JWT/session claim.
"""
from dataclasses import dataclass

from fastapi import Header, Request


@dataclass
class CurrentUser:
    role: str
    name: str


ALLOWED_ROLES = {"billing_staff", "cfo", "compliance", "admin"}


async def get_current_user(x_user_role: str = Header(default="billing_staff")) -> CurrentUser:
    role = x_user_role if x_user_role in ALLOWED_ROLES else "billing_staff"
    return CurrentUser(role=role, name=f"demo-{role}")


async def get_pool(request: Request):
    return request.app.state.pool
