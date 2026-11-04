"""Workflow engine services — definitions, instances, tasks."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from uitop.core.errors import APIError
from uitop.core.ui_rbac import has_perm, is_super_admin_session
from uitop.extensions import db
from uitop.models.user import User
from uitop.models.workflow import (
    TASK_PRIORITIES,
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowInstance,
    WorkTask,
)
from uitop.services.audit import log_audit
from uitop.services.notifications import notify_user


def utcnow():
    return datetime.now(timezone.utc)


RESTORE_STEPS = [
    {
        "key": "submit",
        "label": "Employee submits restore request",
        "type": "submit",
        "creates_task": False,
    },
    {
        "key": "review",
        "label": "IT technician reviews",
        "type": "review",
        "permission": "helpdesk:assign",
        "alt_permission": "backup:manage",
        "creates_task": True,
        "task_title": "Review restore request",
    },
    {
        "key": "execute",
        "label": "Restore executed",
        "type": "execute",
        "permission": "backup:manage",
        "creates_task": True,
        "task_title": "Execute restore",
    },
    {
        "key": "complete",
        "label": "Completed",
        "type": "complete",
        "creates_task": False,
    },
]

SERVICE_REQUEST_STEPS = [
    {
        "key": "submit",
        "label": "Employee submits request",
        "type": "submit",
        "creates_task": False,
    },
    {
        "key": "review",
        "label": "Helpdesk reviews",
        "type": "review",
        "permission": "helpdesk:assign",
        "alt_permission": "helpdesk:write",
        "creates_task": True,
        "task_title": "Review service request",
    },
    {
        "key": "fulfill",
        "label": "IT fulfills request",
        "type": "execute",
        "permission": "helpdesk:assign",
        "alt_permission": "assets:assign",
        "creates_task": True,
        "task_title": "Fulfill service request",
    },
    {
        "key": "complete",
        "label": "Completed",
        "type": "complete",
        "creates_task": False,
    },
]

SOFTWARE_INSTALL_STEPS = [
    {
        "key": "submit",
        "label": "Employee requests software",
        "type": "submit",
        "creates_task": False,
    },
    {
        "key": "review",
        "label": "Helpdesk reviews",
        "type": "review",
        "permission": "helpdesk:assign",
        "alt_permission": "helpdesk:write",
        "creates_task": True,
        "task_title": "Review software request",
    },
    {
        "key": "approve",
        "label": "IT Admin approves",
        "type": "approve",
        "permission": "software:write",
        "alt_permission": "assets:write",
        "creates_task": True,
        "task_title": "Approve software install",
    },
    {
        "key": "install",
        "label": "Software installed",
        "type": "execute",
        "permission": "helpdesk:assign",
        "alt_permission": "assets:write",
        "creates_task": True,
        "task_title": "Install software",
    },
    {
        "key": "complete",
        "label": "Completed",
        "type": "complete",
        "creates_task": False,
    },
]


def _upsert_definition(key: str, name: str, description: str, steps: list[dict]) -> WorkflowDefinition:
    row = WorkflowDefinition.query.filter_by(key=key).first()
    if row is None:
        row = WorkflowDefinition(
            key=key,
            name=name,
            description=description,
            is_active=True,
            steps_json=steps,
        )
        db.session.add(row)
    else:
        row.name = name
        row.description = description
        row.steps_json = steps
        row.is_active = True
    return row


def ensure_workflow_definitions() -> None:
    _upsert_definition(
        "restore_request",
        "Backup Restore Request",
        "Employee requests a file/PC restore; IT reviews and executes.",
        RESTORE_STEPS,
    )
    _upsert_definition(
        "service_request",
        "Service Request",
        "Catalog service requests — helpdesk review then IT fulfillment.",
        SERVICE_REQUEST_STEPS,
    )
    _upsert_definition(
        "software_install",
        "Software Installation",
        "Employee requests software; helpdesk reviews, IT admin approves, then install.",
        SOFTWARE_INSTALL_STEPS,
    )
    db.session.flush()


def _next_number() -> str:
    year = utcnow().year
    prefix = f"WF-{year}-"
    last = (
        WorkflowInstance.query.filter(WorkflowInstance.number.like(f"{prefix}%"))
        .order_by(WorkflowInstance.id.desc())
        .first()
    )
    seq = 1
    if last and last.number:
        try:
            seq = int(last.number.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = WorkflowInstance.query.count() + 1
    return f"{prefix}{seq:04d}"


def start_workflow_request(
    *,
    definition_key: str,
    requester_id: int,
    title: str,
    payload: dict | None = None,
    resource_label: str | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    priority: str = "medium",
    catalog_key: str | None = None,
    notify_roles: list[str] | None = None,
) -> WorkflowInstance:
    """Generic catalog/service workflow starter."""
    defn = get_definition(definition_key)
    steps = steps_for(defn)
    if not steps:
        raise APIError("Workflow has no steps configured")

    requester = db.session.get(User, requester_id)
    body = dict(payload or {})
    body["requester_name"] = requester.full_name if requester else None
    if catalog_key:
        body["catalog_key"] = catalog_key

    inst = WorkflowInstance(
        definition_id=defn.id,
        number=_next_number(),
        title=(title or defn.name).strip()[:255],
        status="in_progress",
        current_step_key=steps[0]["key"],
        priority=priority if priority in TASK_PRIORITIES else "medium",
        requester_user_id=requester_id,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_label=(resource_label or "").strip() or None,
        payload_json=body,
        due_at=utcnow() + timedelta(days=3),
    )
    db.session.add(inst)
    db.session.flush()

    note = body.get("justification") or body.get("reason") or body.get("details")
    _add_event(inst, "submitted", step_key=steps[0]["key"], note=note if isinstance(note, str) else None, actor_id=requester_id)

    review = steps[1] if len(steps) > 1 else None
    if review:
        inst.current_step_key = review["key"]
        inst.status = "waiting"
        _spawn_task_for_step(inst, review, actor_id=requester_id)
        _add_event(inst, "advanced", step_key=review["key"], note="Awaiting IT review", actor_id=requester_id)
        _notify_role_holders(
            notify_roles or ["helpdesk", "operator", "admin"],
            title=f"{defn.name} {inst.number}",
            body=f"{requester.full_name if requester else 'Employee'}: {inst.title}",
            link_url=f"/workflows/{inst.id}",
            resource_id=inst.id,
        )

    db.session.commit()
    log_audit(
        "workflow.started",
        actor_user_id=requester_id,
        resource_type="workflow",
        resource_id=inst.id,
        meta={"number": inst.number, "definition": definition_key, "catalog_key": catalog_key},
    )
    return inst


def start_restore_request(
    *,
    requester_id: int,
    title: str,
    reason: str | None = None,
    resource_label: str | None = None,
    resource_type: str = "computer",
    resource_id: int | None = None,
    priority: str = "medium",
    backup_point: str | None = None,
) -> WorkflowInstance:
    return start_workflow_request(
        definition_key="restore_request",
        requester_id=requester_id,
        title=title or f"Restore request — {(resource_label or 'files').strip()}",
        payload={"reason": (reason or "").strip() or None, "backup_point": (backup_point or "").strip() or None},
        resource_label=resource_label,
        resource_type=resource_type,
        resource_id=resource_id,
        priority=priority,
        catalog_key="backup_restore",
        notify_roles=["helpdesk", "operator", "admin"],
    )


def start_catalog_request(
    *,
    catalog_key: str,
    requester_id: int,
    form: dict,
    priority: str | None = None,
) -> WorkflowInstance:
    from uitop.services.catalog import get_catalog_item

    item = get_catalog_item(catalog_key)
    if not item:
        raise APIError("Unknown catalog item", status_code=404)
    if item.get("redirect"):
        raise APIError("This catalog item uses a dedicated form", status_code=400)

    payload = {}
    for field in item.get("fields") or []:
        name = field.get("name")
        if not name:
            continue
        val = (form.get(name) or "").strip()
        if field.get("required") and not val:
            raise APIError(f"{field.get('label') or name} is required")
        payload[name] = val or None

    title = f"{item['name']}"
    if payload.get("software_name"):
        title = f"{item['name']}: {payload['software_name']}"
    elif payload.get("printer_name"):
        title = f"{item['name']}: {payload['printer_name']}"
    elif payload.get("folder_path"):
        title = f"{item['name']}: {payload['folder_path']}"

    resource_label = (
        payload.get("device")
        or payload.get("printer_name")
        or payload.get("folder_path")
        or payload.get("account")
        or payload.get("display_name")
        or item["name"]
    )

    return start_workflow_request(
        definition_key=item["workflow_key"],
        requester_id=requester_id,
        title=title,
        payload=payload,
        resource_label=resource_label,
        resource_type="catalog",
        priority=priority or item.get("default_priority") or "medium",
        catalog_key=item["key"],
        notify_roles=["helpdesk", "operator", "admin"],
    )


def get_definition(key: str) -> WorkflowDefinition:
    ensure_workflow_definitions()
    row = WorkflowDefinition.query.filter_by(key=key, is_active=True).first()
    if not row:
        raise APIError(f"Workflow '{key}' is not available", status_code=404)
    return row


def steps_for(defn: WorkflowDefinition) -> list[dict]:
    return list(defn.steps_json or [])


def step_index(defn: WorkflowDefinition, key: str | None) -> int:
    for i, s in enumerate(steps_for(defn)):
        if s.get("key") == key:
            return i
    return -1


def current_step(instance: WorkflowInstance) -> dict | None:
    for s in steps_for(instance.definition):
        if s.get("key") == instance.current_step_key:
            return s
    return None


def next_step(instance: WorkflowInstance) -> dict | None:
    steps = steps_for(instance.definition)
    idx = step_index(instance.definition, instance.current_step_key)
    if idx < 0 or idx + 1 >= len(steps):
        return None
    return steps[idx + 1]


def can_act_on_step(step: dict | None, *, user_id: int | None) -> bool:
    if not step or not user_id:
        return False
    if is_super_admin_session():
        return True
    if step.get("type") in ("submit", "complete"):
        return True
    perm = step.get("permission")
    alt = step.get("alt_permission")
    if perm and has_perm(perm):
        return True
    if alt and has_perm(alt):
        return True
    # Requester cannot approve their own review/execute
    return False


def _add_event(instance: WorkflowInstance, action: str, *, step_key: str | None, note: str | None, actor_id: int | None):
    db.session.add(
        WorkflowEvent(
            instance_id=instance.id,
            step_key=step_key,
            action=action,
            note=(note or "").strip() or None,
            actor_user_id=actor_id,
        )
    )


def _spawn_task_for_step(instance: WorkflowInstance, step: dict, *, actor_id: int | None) -> WorkTask | None:
    if not step.get("creates_task"):
        return None
    title = step.get("task_title") or f"{instance.definition.name}: {step.get('label')}"
    due = utcnow() + timedelta(days=1)
    task = WorkTask(
        title=f"{title} — {instance.resource_label or instance.number}",
        description=instance.title,
        status="open",
        priority=instance.priority if instance.priority in TASK_PRIORITIES else "medium",
        created_by_id=actor_id,
        due_at=due,
        source_type="workflow",
        source_id=instance.id,
        workflow_instance_id=instance.id,
        resource_type=instance.resource_type,
        resource_id=instance.resource_id,
        link_url=f"/workflows/{instance.id}",
    )
    db.session.add(task)
    db.session.flush()
    return task


def _notify_role_holders(role_names: list[str], *, title: str, body: str, link_url: str, resource_id: int):
    from uitop.models.role import Role

    users: set[int] = set()
    for name in role_names:
        role = Role.query.filter_by(name=name).first()
        if not role:
            continue
        for u in role.users:
            if u.is_active:
                users.add(u.id)
    # Also notify users with backup manage / helpdesk via super admins lightly
    for uid in users:
        notify_user(
            uid,
            title=title,
            body=body,
            category="workflow",
            link_url=link_url,
            resource_type="workflow",
            resource_id=resource_id,
        )


def advance_instance(
    instance_id: int,
    *,
    action: str,
    actor_id: int | None,
    note: str | None = None,
    assignee_user_id: int | None = None,
) -> WorkflowInstance:
    inst = db.session.get(WorkflowInstance, instance_id)
    if not inst:
        raise APIError("Workflow not found", status_code=404)
    if inst.status in ("completed", "rejected", "cancelled"):
        raise APIError("This workflow is already closed")

    step = current_step(inst)
    action = (action or "").strip().lower()

    if action == "reject":
        if not can_act_on_step(step, user_id=actor_id):
            raise APIError("You cannot reject this step", status_code=403)
        inst.status = "rejected"
        inst.completed_at = utcnow()
        _add_event(inst, "rejected", step_key=inst.current_step_key, note=note, actor_id=actor_id)
        # Close open tasks
        for t in WorkTask.query.filter_by(workflow_instance_id=inst.id, status="open").all():
            t.status = "cancelled"
            t.completed_at = utcnow()
        if inst.requester_user_id:
            notify_user(
                inst.requester_user_id,
                title=f"Request {inst.number} rejected",
                body=note or "IT could not approve this request.",
                category="workflow",
                link_url=f"/workflows/{inst.id}",
                resource_type="workflow",
                resource_id=inst.id,
                actor_id=actor_id,
            )
        db.session.commit()
        log_audit("workflow.rejected", actor_user_id=actor_id, resource_type="workflow", resource_id=inst.id)
        return inst

    if action == "comment":
        _add_event(inst, "commented", step_key=inst.current_step_key, note=note, actor_id=actor_id)
        db.session.commit()
        return inst

    if action == "assign":
        if not can_act_on_step(step, user_id=actor_id):
            raise APIError("You cannot assign this workflow", status_code=403)
        inst.assignee_user_id = assignee_user_id
        _add_event(inst, "assigned", step_key=inst.current_step_key, note=note, actor_id=actor_id)
        for t in WorkTask.query.filter_by(workflow_instance_id=inst.id, status="open").all():
            t.assignee_user_id = assignee_user_id
        if assignee_user_id:
            notify_user(
                assignee_user_id,
                title=f"Assigned: {inst.number}",
                body=inst.title,
                category="workflow",
                link_url=f"/workflows/{inst.id}",
                resource_type="workflow",
                resource_id=inst.id,
                actor_id=actor_id,
            )
        db.session.commit()
        return inst

    if action not in ("approve", "complete", "execute"):
        raise APIError("Unknown action")

    if not can_act_on_step(step, user_id=actor_id):
        raise APIError("You cannot action this step", status_code=403)

    # Complete open tasks for current step
    for t in WorkTask.query.filter_by(workflow_instance_id=inst.id, status="open").all():
        t.status = "done"
        t.completed_at = utcnow()
        if not t.assignee_user_id:
            t.assignee_user_id = actor_id

    _add_event(
        inst,
        "approved" if action == "approve" else action,
        step_key=inst.current_step_key,
        note=note,
        actor_id=actor_id,
    )

    nxt = next_step(inst)
    if nxt is None or nxt.get("type") == "complete":
        inst.current_step_key = "complete"
        inst.status = "completed"
        inst.completed_at = utcnow()
        _add_event(inst, "completed", step_key="complete", note=note, actor_id=actor_id)
        if inst.requester_user_id:
            notify_user(
                inst.requester_user_id,
                title=f"Request completed — {inst.number}",
                body=f"Your request “{inst.title}” is done.",
                category="workflow",
                link_url=f"/workflows/{inst.id}",
                resource_type="workflow",
                resource_id=inst.id,
                actor_id=actor_id,
            )
    else:
        inst.current_step_key = nxt["key"]
        inst.status = "waiting" if nxt.get("type") in ("review", "approve") else "in_progress"
        _spawn_task_for_step(inst, nxt, actor_id=actor_id)
        _add_event(inst, "advanced", step_key=nxt["key"], note=f"Moved to {nxt.get('label')}", actor_id=actor_id)
        if nxt.get("type") == "execute":
            _notify_role_holders(
                ["operator", "admin", "helpdesk"],
                title=f"Action needed: {inst.number}",
                body=f"{nxt.get('label') or 'Execute'}: {inst.title}",
                link_url=f"/workflows/{inst.id}",
                resource_id=inst.id,
            )

    db.session.commit()
    log_audit(
        f"workflow.{action}",
        actor_user_id=actor_id,
        resource_type="workflow",
        resource_id=inst.id,
        meta={"step": inst.current_step_key, "status": inst.status},
    )
    return inst


def list_instances(
    *,
    requester_user_id: int | None = None,
    status: str | None = None,
    definition_key: str | None = None,
    limit: int = 100,
) -> list[WorkflowInstance]:
    ensure_workflow_definitions()
    q = WorkflowInstance.query.order_by(WorkflowInstance.updated_at.desc())
    if requester_user_id:
        q = q.filter_by(requester_user_id=requester_user_id)
    if status:
        q = q.filter_by(status=status)
    if definition_key:
        defn = WorkflowDefinition.query.filter_by(key=definition_key).first()
        if defn:
            q = q.filter_by(definition_id=defn.id)
    return q.limit(limit).all()


def list_tasks(
    *,
    assignee_user_id: int | None = None,
    mine_created: int | None = None,
    status: str | None = None,
    open_only: bool = False,
    limit: int = 100,
) -> list[WorkTask]:
    q = WorkTask.query.order_by(WorkTask.created_at.desc())
    if assignee_user_id:
        q = q.filter_by(assignee_user_id=assignee_user_id)
    if mine_created:
        q = q.filter_by(created_by_id=mine_created)
    if status:
        q = q.filter_by(status=status)
    if open_only:
        q = q.filter(WorkTask.status.in_(("open", "in_progress")))
    return q.limit(limit).all()


def update_task(
    task_id: int,
    *,
    actor_id: int | None,
    status: str | None = None,
    assignee_user_id: int | None = None,
    priority: str | None = None,
) -> WorkTask:
    task = db.session.get(WorkTask, task_id)
    if not task:
        raise APIError("Task not found", status_code=404)
    if status:
        if status not in ("open", "in_progress", "done", "cancelled"):
            raise APIError("Invalid status")
        task.status = status
        if status in ("done", "cancelled"):
            task.completed_at = utcnow()
    if assignee_user_id is not None:
        task.assignee_user_id = assignee_user_id or None
    if priority and priority in TASK_PRIORITIES:
        task.priority = priority
    task.updated_at = utcnow()
    db.session.commit()
    log_audit("task.updated", actor_user_id=actor_id, resource_type="task", resource_id=task.id)
    return task


def serialize_instance_detail(inst: WorkflowInstance) -> dict:
    data = inst.to_dict()
    data["steps"] = steps_for(inst.definition)
    data["events"] = [e.to_dict() for e in inst.events.order_by(WorkflowEvent.created_at.asc()).all()]
    data["tasks"] = [t.to_dict() for t in inst.tasks.order_by(WorkTask.id.asc()).all()]
    data["current_step"] = current_step(inst)
    return data
