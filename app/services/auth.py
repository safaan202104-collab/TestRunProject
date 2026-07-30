"""
Auth Service — Role-Based Access Control (RBAC).
Provides helper utilities to verify permissions and roles for sensitive actions.
"""
from enum import Enum
from typing import Set, Dict, Optional
from fastapi import Header, HTTPException, status

class Role(str, Enum):
    RECEPTIONIST = "receptionist"
    CLINIC_MANAGER = "clinic_manager"
    ADMINISTRATOR = "administrator"
    DEVELOPER = "developer"

class Permission(str, Enum):
    APPROVE_BOOKING = "approve_booking"
    OVERRIDE_AI = "override_ai"
    MODIFY_CONFIG = "modify_config"
    ACCESS_ANALYTICS = "access_analytics"
    RUN_EVALS = "run_evals"

# Assign permissions to roles
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.RECEPTIONIST: {
        Permission.APPROVE_BOOKING,
    },
    Role.CLINIC_MANAGER: {
        Permission.APPROVE_BOOKING,
        Permission.OVERRIDE_AI,
        Permission.ACCESS_ANALYTICS,
    },
    Role.ADMINISTRATOR: {
        Permission.APPROVE_BOOKING,
        Permission.OVERRIDE_AI,
        Permission.ACCESS_ANALYTICS,
        Permission.MODIFY_CONFIG,
    },
    Role.DEVELOPER: {
        Permission.APPROVE_BOOKING,
        Permission.OVERRIDE_AI,
        Permission.ACCESS_ANALYTICS,
        Permission.MODIFY_CONFIG,
        Permission.RUN_EVALS,
    }
}

# Simplified Token map for development/testing convenience
DEVELOPMENT_TOKENS = {
    "dev-token-receptionist": Role.RECEPTIONIST,
    "dev-token-manager": Role.CLINIC_MANAGER,
    "dev-token-admin": Role.ADMINISTRATOR,
    "dev-token-developer": Role.DEVELOPER,
}

def get_role_from_token(token: str) -> Optional[Role]:
    """Resolves a Bearer/auth token to a Role."""
    if token.startswith("Bearer "):
        token = token[7:]
    return DEVELOPMENT_TOKENS.get(token)

def verify_permission(token: str, required_permission: Permission) -> None:
    """Verifies that the token matches a role with the required permission."""
    role = get_role_from_token(token)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token."
        )
        
    permissions = ROLE_PERMISSIONS.get(role, set())
    if required_permission not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role.value}' does not have the '{required_permission.value}' permission required for this action."
        )
