"""Backup & Restore — ops center mock data."""
from __future__ import annotations


def kpis() -> dict:
    return {
        "protected_devices": 186,
        "successful": 172,
        "failed": 5,
        "storage_tb": 12.4,
        "recovery_points": 1482,
        "restore_jobs": 3,
    }


def backup_jobs() -> list[dict]:
    return [
        {
            "id": 1,
            "name": "Daily Server Backup",
            "target": "SRV-001",
            "target_type": "Server",
            "type": "Full",
            "last_backup": "Today 02:00",
            "status": "Success",
            "schedule": "Daily 02:00",
            "policy": "Servers · 90-day retain",
            "storage": "NAS-01",
            "size_gb": 84.2,
        },
        {
            "id": 2,
            "name": "Finance PCs",
            "target": "Finance Department",
            "target_type": "Department",
            "type": "Incremental",
            "last_backup": "Today 09:15",
            "status": "Running",
            "schedule": "Weekdays 09:00",
            "policy": "Workstations · 30-day retain",
            "storage": "Local Storage",
            "size_gb": 12.1,
            "progress": 62,
        },
        {
            "id": 3,
            "name": "SQL Weekly Archive",
            "target": "SQL-PROD",
            "target_type": "Database",
            "type": "Full",
            "last_backup": "Sat 23:00",
            "status": "Success",
            "schedule": "Weekly Sat 23:00",
            "policy": "Databases · Encrypt",
            "storage": "Azure Blob",
            "size_gb": 210.5,
        },
        {
            "id": 4,
            "name": "Workstation Image — HQ",
            "target": "HQ Workstations",
            "target_type": "Workstations",
            "type": "Incremental",
            "last_backup": "Yesterday 23:00",
            "status": "Failed",
            "schedule": "Daily 23:00",
            "policy": "Workstations · 30-day retain",
            "storage": "NAS-01",
            "size_gb": 0,
            "error": "Agent offline on PC-088",
        },
        {
            "id": 5,
            "name": "VM Cluster Snapshot",
            "target": "VMware Cluster A",
            "target_type": "Virtual Machines",
            "type": "Snapshot",
            "last_backup": "Today 01:30",
            "status": "Success",
            "schedule": "Daily 01:30",
            "policy": "VMs · 14-day retain",
            "storage": "AWS S3",
            "size_gb": 640.0,
        },
    ]


def restore_jobs() -> list[dict]:
    return [
        {
            "id": 101,
            "device": "SRV-001",
            "point": "22 Jul 2026 02:00",
            "started": "Yesterday 14:20",
            "status": "Completed",
            "progress": 100,
            "requested_by": "S. Dlamini",
        },
        {
            "id": 102,
            "device": "PC-022",
            "point": "21 Jul 2026 23:00",
            "started": "Today 08:05",
            "status": "Running",
            "progress": 47,
            "requested_by": "Helpdesk",
        },
        {
            "id": 103,
            "device": "SQL-PROD",
            "point": "19 Jul 2026 23:00",
            "started": "Today 10:40",
            "status": "Queued",
            "progress": 0,
            "requested_by": "Thandi Nkosi",
        },
    ]


def recovery_points() -> list[dict]:
    return [
        {"id": 201, "device": "PC-001", "when": "22 Jul 2026 23:00", "type": "Incremental", "size_gb": 4.2, "job": "Finance PCs"},
        {"id": 202, "device": "PC-001", "when": "21 Jul 2026 23:00", "type": "Incremental", "size_gb": 3.8, "job": "Finance PCs"},
        {"id": 203, "device": "SRV-001", "when": "22 Jul 2026 02:00", "type": "Full", "size_gb": 84.2, "job": "Daily Server Backup"},
        {"id": 204, "device": "SRV-001", "when": "21 Jul 2026 02:00", "type": "Full", "size_gb": 83.9, "job": "Daily Server Backup"},
        {"id": 205, "device": "SQL-PROD", "when": "19 Jul 2026 23:00", "type": "Full", "size_gb": 210.5, "job": "SQL Weekly Archive"},
        {"id": 206, "device": "PC-022", "when": "21 Jul 2026 23:00", "type": "Incremental", "size_gb": 2.1, "job": "Workstation Image — HQ"},
    ]


def schedules() -> list[dict]:
    return [
        {"name": "Daily servers", "cadence": "Daily", "time": "02:00", "scope": "Servers", "enabled": True},
        {"name": "Weekday finance", "cadence": "Weekdays", "time": "09:00", "scope": "Finance PCs", "enabled": True},
        {"name": "Weekly SQL", "cadence": "Weekly", "time": "Sat 23:00", "scope": "Databases", "enabled": True},
        {"name": "Monthly archive", "cadence": "Monthly", "time": "1st 01:00", "scope": "Archive to Azure", "enabled": False},
    ]


def storage() -> list[dict]:
    return [
        {"name": "Local Storage", "type": "Local", "used_tb": 2.1, "capacity_tb": 4.0, "status": "Healthy"},
        {"name": "NAS-01", "type": "NAS", "used_tb": 6.8, "capacity_tb": 10.0, "status": "Healthy"},
        {"name": "Azure Blob", "type": "Cloud", "used_tb": 1.9, "capacity_tb": 5.0, "status": "Healthy"},
        {"name": "AWS S3", "type": "Cloud", "used_tb": 1.4, "capacity_tb": 5.0, "status": "Healthy"},
        {"name": "Offsite USB archive", "type": "External", "used_tb": 0.2, "capacity_tb": 2.0, "status": "Idle"},
    ]


def policies() -> list[dict]:
    return [
        {"name": "Servers", "schedule": "Daily Full", "retain_days": 90, "encrypt": True, "scope": "Servers"},
        {"name": "Workstations", "schedule": "Daily Incremental", "retain_days": 30, "encrypt": True, "scope": "Workstations"},
        {"name": "Databases", "schedule": "Weekly Full", "retain_days": 180, "encrypt": True, "scope": "Databases"},
        {"name": "Virtual Machines", "schedule": "Daily Snapshot", "retain_days": 14, "encrypt": False, "scope": "VMs"},
    ]


def history() -> list[dict]:
    return [
        {"when": "Today 10:40", "title": "Restore queued — SQL-PROD", "meta": "Point 19 Jul 23:00", "tone": ""},
        {"when": "Today 08:05", "title": "Restore running — PC-022", "meta": "47% complete", "tone": "warning"},
        {"when": "Today 02:00", "title": "Backup success — SRV-001", "meta": "84.2 GB · NAS-01", "tone": "success"},
        {"when": "Yesterday 23:10", "title": "Backup failed — PC-088", "meta": "Agent offline", "tone": "danger"},
        {"when": "Yesterday 14:55", "title": "Restore completed — SRV-001", "meta": "Requested by S. Dlamini", "tone": "success"},
    ]


def get_job(job_id: int) -> dict | None:
    for j in backup_jobs():
        if j["id"] == job_id:
            return j
    return None


def build_module_payload() -> dict:
    return {
        "kpis": kpis(),
        "jobs": backup_jobs(),
        "restores": restore_jobs(),
        "points": recovery_points(),
        "schedules": schedules(),
        "storage": storage(),
        "policies": policies(),
        "history": history(),
    }
