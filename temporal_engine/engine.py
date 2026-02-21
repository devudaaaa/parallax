"""
GTRBAC Engine — Temporal Constraint & Activation Engine for the Digital Twin.

Direct implementation of the GTRBAC model from:
  Joshi, J.B.D., Bertino, E., Latif, U., & Ghafoor, A. (2005).
  A generalized temporal role-based access control model.
  IEEE Transactions on Knowledge and Data Engineering, 17(1), 4-23.

As researched and applied to AIT by Ade (Temporal Extension for RBAC).

The engine implements:
  1. Role State Machine: Disabled → Enabled → Active (Figure 2.3)
  2. TCAB (Temporal Constraint and Activation Base)
  3. Operation Pool (OP) — predefined system operations
  4. Constraint Operation Pool (COP) — constraint management
  5. Conflict Resolution — priority-based + negative-takes-precedence
  6. Triggers — dependent event activation

Applied to the Digital Twin:
  - "Roles" become twin behavioral modes (professional, casual, reflective, etc.)
  - "Users" become requesters/callers (Slack, Discord, API, etc.)
  - "Permissions" become access tiers (public, friends, close, private)
  - The engine tick (τ) runs every minute, evaluating all constraints
  - Temporal constraints govern WHEN each mode/tier is available
  - Triggers handle dependent activations (e.g., "work mode" → "professional tier")
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Callable, Optional
from loguru import logger

from temporal_engine.calendars import (
    PeriodicExpression, TimeInterval, Duration, CalendarUnit,
    PeriodicExpressions,
)


# ═══════════════════════════════════════════════════════════
# Role States — Figure 2.3 from the AIT research
# ═══════════════════════════════════════════════════════════

class RoleState(Enum):
    """
    States of a role in the GTRBAC model.
    
    From the AIT research, Figure 2.3:
        Disabled ←→ Enabled ←→ Active
        
    - Disabled: no user can use it in any session
    - Enabled: designated users CAN activate it
    - Active: at least one user has activated it
    
    Transitions:
        enable:     Disabled → Enabled
        disable:    Enabled → Disabled, Active → Disabled
        activate:   Enabled → Active
        deactivate: Active → Enabled, Active → Active (if other users)
    """
    DISABLED = auto()
    ENABLED = auto()
    ACTIVE = auto()


# ═══════════════════════════════════════════════════════════
# System Operations — the 4 pairs from GTRBAC
# ═══════════════════════════════════════════════════════════

class OperationMode(str, Enum):
    """
    System operations from the GTRBAC engine (Section 4.6.2).
    
    "We define 4 pairs of system operations, and the two operations
     in each pair is the inverse operation of each other"
    
    Applied to Digital Twin:
        Role enable/disable    → Twin mode enable/disable
        User-role assign       → Caller gets access tier
        Role-permission assign → Mode gets capabilities
        Role activate          → Mode becomes current active mode
    """
    # Role (Mode) management
    ENABLE_ROLE = "enableRole"
    DISABLE_ROLE = "disableRole"
    ACTIVATE_ROLE = "activateRole"
    DEACTIVATE_ROLE = "deactivateRole"

    # User-Role (Caller-Mode) assignment
    ASSIGN_USER = "assignUser"
    DEASSIGN_USER = "deassignUser"

    # Role-Permission (Mode-Tier) assignment
    ASSIGN_PERMISSION = "assignPermission"
    DEASSIGN_PERMISSION = "deassignPermission"


# Inverse operation pairs (for conflict resolution)
INVERSE_OPERATIONS = {
    OperationMode.ENABLE_ROLE: OperationMode.DISABLE_ROLE,
    OperationMode.DISABLE_ROLE: OperationMode.ENABLE_ROLE,
    OperationMode.ACTIVATE_ROLE: OperationMode.DEACTIVATE_ROLE,
    OperationMode.DEACTIVATE_ROLE: OperationMode.ACTIVATE_ROLE,
    OperationMode.ASSIGN_USER: OperationMode.DEASSIGN_USER,
    OperationMode.DEASSIGN_USER: OperationMode.ASSIGN_USER,
    OperationMode.ASSIGN_PERMISSION: OperationMode.DEASSIGN_PERMISSION,
    OperationMode.DEASSIGN_PERMISSION: OperationMode.ASSIGN_PERMISSION,
}

# Negative operations (for negative-takes-precedence rule)
NEGATIVE_OPERATIONS = {
    OperationMode.DISABLE_ROLE,
    OperationMode.DEACTIVATE_ROLE,
    OperationMode.DEASSIGN_USER,
    OperationMode.DEASSIGN_PERMISSION,
}


@dataclass
class Operation:
    """
    A system operation in the Operation Pool (OP).
    
    Structure: <mode, target, subject, priority>
    """
    mode: OperationMode
    target: str           # role/mode name
    subject: str = ""     # user/permission name (optional per mode)
    priority: int = 0     # higher = more important
    source: str = ""      # what generated this operation

    @property
    def is_negative(self) -> bool:
        return self.mode in NEGATIVE_OPERATIONS

    def conflicts_with(self, other: Operation) -> bool:
        """Check if this operation conflicts with another."""
        if self.target != other.target:
            return False
        if self.subject and other.subject and self.subject != other.subject:
            return False
        return INVERSE_OPERATIONS.get(self.mode) == other.mode

    def __repr__(self):
        parts = [f"<{self.mode.value}", self.target]
        if self.subject:
            parts.append(self.subject)
        if self.priority:
            parts.append(f"pri:{self.priority}")
        return ", ".join(parts) + ">"


# ═══════════════════════════════════════════════════════════
# Temporal Constraints
# ═══════════════════════════════════════════════════════════

@dataclass
class TemporalConstraint:
    """
    A temporal constraint from the TCAB.
    
    Form: (I, P, pr:E) or ([I,P,|D], D_x, pr:E)
    
    Where:
        I = time interval (bounding)
        P = periodic expression
        D_x = duration restriction
        pr:E = prioritized event expression
    """
    name: str
    periodic: PeriodicExpression
    event_mode: OperationMode
    target: str               # what role/mode this applies to
    subject: str = ""         # user/permission if applicable
    priority: int = 0
    duration_limit: Duration | None = None
    enabled: bool = True

    def is_active_at(self, t: datetime) -> bool:
        """Check if this constraint is active at time t."""
        return self.enabled and self.periodic.is_active(t)

    def generate_operation(self) -> Operation:
        """Generate the system operation for this constraint."""
        return Operation(
            mode=self.event_mode,
            target=self.target,
            subject=self.subject,
            priority=self.priority,
            source=f"constraint:{self.name}",
        )

    def generate_inverse_operation(self) -> Operation:
        """Generate the inverse operation (when constraint is NOT active)."""
        inverse_mode = INVERSE_OPERATIONS[self.event_mode]
        return Operation(
            mode=inverse_mode,
            target=self.target,
            subject=self.subject,
            priority=self.priority,
            source=f"constraint:{self.name}:inverse",
        )


# ═══════════════════════════════════════════════════════════
# Triggers — Event Dependencies
# ═══════════════════════════════════════════════════════════

@dataclass
class Trigger:
    """
    Trigger expression from GTRBAC.
    
    Form: E1, ..., En, C1, ..., Ck → pr:E after Δt
    
    "Triggers for dependent roles: e.g., Night-shift nurse role
     will also trigger to enable when Night-shift doctor role is enabled.
     It also captures past events and defines future events."
    
    Applied to Digital Twin:
        - "professional_mode" ACTIVE → enable "formal_tier"
        - "evening_mode" ACTIVE → enable "reflective_personality"
        - "close_friend_detected" → upgrade access tier to "close"
    """
    name: str

    # Conditions (all must be true)
    conditions: list[tuple[str, RoleState]]   # (role_name, required_state)

    # What this trigger fires
    fire_mode: OperationMode
    fire_target: str
    fire_subject: str = ""
    fire_priority: int = 0

    # Delay before firing
    delay_minutes: int = 0

    def evaluate(self, role_states: dict[str, RoleState]) -> Operation | None:
        """
        Evaluate the trigger against current role states.
        Returns an Operation if all conditions are met, None otherwise.
        """
        for role_name, required_state in self.conditions:
            current_state = role_states.get(role_name, RoleState.DISABLED)
            if current_state != required_state:
                return None

        return Operation(
            mode=self.fire_mode,
            target=self.fire_target,
            subject=self.fire_subject,
            priority=self.fire_priority,
            source=f"trigger:{self.name}",
        )


# ═══════════════════════════════════════════════════════════
# Role (Mode) Snapshot — tracks current state
# ═══════════════════════════════════════════════════════════

@dataclass
class RoleSnapshot:
    """
    Current state of a role/mode.
    
    From the GTRBAC semantics: "ST(t) contains effect of the events
    in Nonblocked(EV(t)) on ST(t-1)"
    """
    name: str
    state: RoleState = RoleState.DISABLED
    active_users: set[str] = field(default_factory=set)
    permissions: set[str] = field(default_factory=set)
    last_enabled: datetime | None = None
    last_activated: datetime | None = None
    last_disabled: datetime | None = None
    activation_count: int = 0


# ═══════════════════════════════════════════════════════════
# GTRBAC Engine — The Core Clock
# ═══════════════════════════════════════════════════════════

class GTRBACEngine:
    """
    The GTRBAC Engine — Temporal Clock of the Digital Twin.
    
    Implements the two-step process from Figure 4.2:
    
    Step 1: Check Constraint Operation Pool (COP)
        - Check constraint enabling/disabling run-time requests
        - Check constraints on constraints
        - Resolve conflicts in COP
        - Update enabling states of constraints
    
    Step 2: Check Operation Pool (OP)
        - Check run-time requests → add to OP
        - Check periodicity constraints → add to OP
        - Check duration constraints → add to OP
        - Resolve conflicts in OP
        - Check triggers → add to OP
        - Resolve conflicts again (triggers may create new conflicts)
        - Check cardinality constraints → remove from OP
        - Update RBAC policy (role states, assignments)
    
    "We choose to run the engine every 1 minute in the current
     implementation. We believe this frequency is high enough to
     capture all constraints and run-time requests in the system."
    """

    def __init__(self, tick_interval_seconds: int = 60):
        # τ — tick interval
        self.tick_interval = tick_interval_seconds

        # Role/Mode states: ST(t)
        self.roles: dict[str, RoleSnapshot] = {}

        # TCAB components
        self.constraints: dict[str, TemporalConstraint] = {}
        self.triggers: list[Trigger] = []

        # Runtime request queue: RQ(t)
        self._runtime_requests: list[Operation] = []

        # Event listeners
        self._listeners: list[Callable] = []

        # Engine state
        self._running = False
        self._thread: threading.Thread | None = None
        self._tick_count = 0

        logger.info(f"GTRBAC Engine initialized (τ = {tick_interval_seconds}s)")

    # ── Role/Mode Management ───────────────────────────────

    def register_role(self, name: str, initial_state: RoleState = RoleState.DISABLED):
        """Register a role/mode in the system."""
        self.roles[name] = RoleSnapshot(name=name, state=initial_state)
        logger.debug(f"Role registered: {name} ({initial_state.name})")

    def add_constraint(self, constraint: TemporalConstraint):
        """Add a temporal constraint to the TCAB."""
        self.constraints[constraint.name] = constraint
        # Ensure the target role exists
        if constraint.target not in self.roles:
            self.register_role(constraint.target)
        logger.debug(f"Constraint added: {constraint.name}")

    def add_trigger(self, trigger: Trigger):
        """Add a trigger to the TCAB."""
        self.triggers.append(trigger)
        logger.debug(f"Trigger added: {trigger.name}")

    def submit_request(self, operation: Operation):
        """
        Submit a run-time request.
        
        "The administrator can also make run-time requests in the system
         which can be dynamic"
        """
        self._runtime_requests.append(operation)
        logger.debug(f"Runtime request queued: {operation}")

    def on_state_change(self, listener: Callable):
        """Register a listener for state changes."""
        self._listeners.append(listener)

    # ── Engine Tick ────────────────────────────────────────

    def tick(self, t: datetime | None = None):
        """
        Execute one engine tick — evaluate all constraints at time t.
        
        This is the heartbeat of the system, running every τ seconds.
        Implements the two-step process from Figure 4.2.
        """
        t = t or datetime.now()
        self._tick_count += 1

        # ── Step 1: Constraint Operation Pool (COP) ───────
        cop: list[Operation] = []

        # Check constraint enabling/disabling requests
        constraint_requests = [
            r for r in self._runtime_requests
            if r.mode in (OperationMode.ENABLE_ROLE, OperationMode.DISABLE_ROLE)
            and r.source.startswith("constraint_control:")
        ]
        cop.extend(constraint_requests)

        # Resolve COP conflicts
        cop = self._resolve_conflicts(cop)

        # Update constraint enabling states
        for op in cop:
            if op.target in self.constraints:
                self.constraints[op.target].enabled = (
                    op.mode == OperationMode.ENABLE_ROLE
                )

        # ── Step 2: Operation Pool (OP) ───────────────────
        op_pool: list[Operation] = []

        # 2a. Add runtime requests (non-constraint-control)
        regular_requests = [
            r for r in self._runtime_requests
            if not r.source.startswith("constraint_control:")
        ]
        op_pool.extend(regular_requests)

        # 2b. Check periodicity constraints
        for name, constraint in self.constraints.items():
            if not constraint.enabled:
                continue
            if constraint.is_active_at(t):
                op_pool.append(constraint.generate_operation())
            else:
                op_pool.append(constraint.generate_inverse_operation())

        # 2c. First conflict resolution (before triggers)
        op_pool = self._resolve_conflicts(op_pool)

        # 2d. Check triggers
        current_states = {name: r.state for name, r in self.roles.items()}
        for trigger in self.triggers:
            fired_op = trigger.evaluate(current_states)
            if fired_op:
                op_pool.append(fired_op)

        # 2e. Second conflict resolution (after triggers)
        op_pool = self._resolve_conflicts(op_pool)

        # 2f. Execute operations — update role states
        changes = self._execute_operations(op_pool, t)

        # Clear processed requests
        self._runtime_requests.clear()

        # Notify listeners of any changes
        if changes:
            for listener in self._listeners:
                try:
                    listener(changes, t)
                except Exception as e:
                    logger.error(f"Listener error: {e}")

        return changes

    def _resolve_conflicts(self, operations: list[Operation]) -> list[Operation]:
        """
        Resolve conflicts in the operation pool.
        
        From the GTRBAC engine:
        1. Higher priority overrides lower priority
        2. Negative (disable) overrides positive (negative-takes-precedence)
        """
        if not operations:
            return []

        # Group operations by target
        by_target: dict[str, list[Operation]] = {}
        for op in operations:
            key = f"{op.target}:{op.subject}"
            if key not in by_target:
                by_target[key] = []
            by_target[key].append(op)

        resolved = []
        for key, ops in by_target.items():
            if len(ops) == 1:
                resolved.append(ops[0])
                continue

            # Check for conflicting pairs
            non_conflicting = []
            conflict_groups = []

            for op in ops:
                found_conflict = False
                for group in conflict_groups:
                    if any(op.conflicts_with(existing) for existing in group):
                        group.append(op)
                        found_conflict = True
                        break
                if not found_conflict:
                    # Check against non-conflicting
                    has_conflict = False
                    for existing in non_conflicting[:]:
                        if op.conflicts_with(existing):
                            conflict_groups.append([existing, op])
                            non_conflicting.remove(existing)
                            has_conflict = True
                            break
                    if not has_conflict:
                        non_conflicting.append(op)

            resolved.extend(non_conflicting)

            # Resolve each conflict group
            for group in conflict_groups:
                # Rule 1: Higher priority wins
                max_priority = max(op.priority for op in group)
                top_priority = [op for op in group if op.priority == max_priority]

                if len(top_priority) == 1:
                    resolved.append(top_priority[0])
                else:
                    # Rule 2: Negative takes precedence
                    negatives = [op for op in top_priority if op.is_negative]
                    if negatives:
                        resolved.append(negatives[0])
                    else:
                        resolved.append(top_priority[0])

        return resolved

    def _execute_operations(
        self, operations: list[Operation], t: datetime
    ) -> list[dict]:
        """Execute resolved operations and update role states."""
        changes = []

        for op in operations:
            role = self.roles.get(op.target)
            if not role:
                continue

            old_state = role.state

            if op.mode == OperationMode.ENABLE_ROLE:
                if role.state == RoleState.DISABLED:
                    role.state = RoleState.ENABLED
                    role.last_enabled = t

            elif op.mode == OperationMode.DISABLE_ROLE:
                if role.state in (RoleState.ENABLED, RoleState.ACTIVE):
                    role.state = RoleState.DISABLED
                    role.active_users.clear()
                    role.last_disabled = t

            elif op.mode == OperationMode.ACTIVATE_ROLE:
                if role.state in (RoleState.ENABLED, RoleState.ACTIVE):
                    role.state = RoleState.ACTIVE
                    if op.subject:
                        role.active_users.add(op.subject)
                    role.last_activated = t
                    role.activation_count += 1

            elif op.mode == OperationMode.DEACTIVATE_ROLE:
                if role.state == RoleState.ACTIVE:
                    if op.subject:
                        role.active_users.discard(op.subject)
                    if not role.active_users:
                        role.state = RoleState.ENABLED

            elif op.mode == OperationMode.ASSIGN_PERMISSION:
                if op.subject:
                    role.permissions.add(op.subject)

            elif op.mode == OperationMode.DEASSIGN_PERMISSION:
                if op.subject:
                    role.permissions.discard(op.subject)

            if role.state != old_state:
                changes.append({
                    "role": role.name,
                    "old_state": old_state.name,
                    "new_state": role.state.name,
                    "operation": str(op),
                    "time": t.isoformat(),
                })
                logger.info(
                    f"⏰ [{t.strftime('%H:%M')}] "
                    f"{role.name}: {old_state.name} → {role.state.name} "
                    f"(via {op.source})"
                )

        return changes

    # ── Engine Loop ────────────────────────────────────────

    def start(self):
        """
        Start the engine loop.
        
        "We choose to run the engine every 1 minute."
        """
        if self._running:
            logger.warning("Engine already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"⏰ GTRBAC Engine started (tick every {self.tick_interval}s)")

    def stop(self):
        """Stop the engine loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.tick_interval + 1)
        logger.info(f"GTRBAC Engine stopped after {self._tick_count} ticks")

    def _run_loop(self):
        """Main engine loop — runs every τ seconds."""
        while self._running:
            try:
                self.tick()
            except Exception as e:
                logger.error(f"Engine tick error: {e}")
            time.sleep(self.tick_interval)

    # ── Query Interface ────────────────────────────────────

    def get_active_roles(self) -> list[str]:
        """Get all currently active roles/modes."""
        return [name for name, r in self.roles.items() if r.state == RoleState.ACTIVE]

    def get_enabled_roles(self) -> list[str]:
        """Get all enabled (but not necessarily active) roles."""
        return [
            name for name, r in self.roles.items()
            if r.state in (RoleState.ENABLED, RoleState.ACTIVE)
        ]

    def get_role_state(self, role_name: str) -> RoleState | None:
        """Get the current state of a specific role."""
        role = self.roles.get(role_name)
        return role.state if role else None

    def get_current_access_tier(self) -> str:
        """
        Determine the current access tier based on active/enabled roles.
        
        In the digital twin context (single user), ENABLED = available.
        We check both ACTIVE and ENABLED since the twin auto-uses modes.
        """
        tier_priority = ["private", "close", "friends", "public"]

        for tier in tier_priority:
            tier_role = f"tier_{tier}"
            role = self.roles.get(tier_role)
            if role and role.state in (RoleState.ACTIVE, RoleState.ENABLED):
                return tier

        return "public"

    def get_current_personality_mode(self) -> str:
        """
        Get the currently active personality mode.
        
        In the digital twin, a mode that is ENABLED is effectively active
        since there's only one "user" (the twin itself). This differs from
        multi-user RBAC where enabled ≠ active.
        """
        modes = ["reflective", "creative", "casual", "professional"]
        for mode in modes:
            mode_role = f"mode_{mode}"
            role = self.roles.get(mode_role)
            if role and role.state in (RoleState.ACTIVE, RoleState.ENABLED):
                return mode
        return "default"

    def get_status(self) -> dict:
        """Full engine status dump."""
        return {
            "tick_count": self._tick_count,
            "running": self._running,
            "tick_interval_seconds": self.tick_interval,
            "roles": {
                name: {
                    "state": r.state.name,
                    "active_users": list(r.active_users),
                    "permissions": list(r.permissions),
                    "activation_count": r.activation_count,
                }
                for name, r in self.roles.items()
            },
            "constraints": {
                name: {
                    "enabled": c.enabled,
                    "active_now": c.is_active_at(datetime.now()),
                    "target": c.target,
                    "event": c.event_mode.value,
                }
                for name, c in self.constraints.items()
            },
            "triggers": len(self.triggers),
            "current_access_tier": self.get_current_access_tier(),
            "current_personality_mode": self.get_current_personality_mode(),
        }
