"""Knowledge base service for Helpdesk."""
from __future__ import annotations

import re

from uitop.core.errors import NotFoundError, ValidationError
from uitop.extensions import db
from uitop.models.helpdesk import KB_CATEGORIES, KnowledgeArticle


def _slugify(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-") or "article"
    slug = base[:240]
    existing = KnowledgeArticle.query.filter_by(slug=slug).first()
    if not existing:
        return slug
    n = 2
    while KnowledgeArticle.query.filter_by(slug=f"{slug}-{n}").first():
        n += 1
    return f"{slug}-{n}"


def list_articles(
    *,
    q: str | None = None,
    category: str | None = None,
    published_only: bool = True,
    limit: int = 100,
) -> list[KnowledgeArticle]:
    query = KnowledgeArticle.query
    if published_only:
        query = query.filter_by(is_published=True)
    if category:
        query = query.filter_by(category=category.lower())
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            db.or_(
                KnowledgeArticle.title.ilike(like),
                KnowledgeArticle.summary.ilike(like),
                KnowledgeArticle.body.ilike(like),
                KnowledgeArticle.tags.ilike(like),
            )
        )
    return query.order_by(KnowledgeArticle.updated_at.desc()).limit(limit).all()


def get_article(article_id: int) -> KnowledgeArticle:
    article = db.session.get(KnowledgeArticle, article_id)
    if article is None:
        raise NotFoundError("Article not found")
    return article


def create_article(
    *,
    title: str,
    body: str,
    summary: str | None = None,
    category: str = "general",
    tags: str | None = None,
    is_published: bool = True,
    author_user_id: int | None = None,
) -> KnowledgeArticle:
    title = (title or "").strip()
    body = (body or "").strip()
    if not title:
        raise ValidationError("Title is required")
    if not body:
        raise ValidationError("Article body is required")
    category = (category or "general").lower()
    if category not in KB_CATEGORIES:
        category = "general"
    article = KnowledgeArticle(
        title=title,
        slug=_slugify(title),
        summary=(summary or "").strip() or None,
        body=body,
        category=category,
        tags=(tags or "").strip() or None,
        is_published=bool(is_published),
        author_user_id=author_user_id,
    )
    db.session.add(article)
    db.session.commit()
    return article


def update_article(article_id: int, data: dict) -> KnowledgeArticle:
    article = get_article(article_id)
    if "title" in data and data["title"]:
        new_title = data["title"].strip()
        if new_title != article.title:
            article.title = new_title
            article.slug = _slugify(new_title)
    if "body" in data and data["body"] is not None:
        body = data["body"].strip()
        if not body:
            raise ValidationError("Article body is required")
        article.body = body
    if "summary" in data:
        article.summary = (data["summary"] or "").strip() or None
    if "category" in data and data["category"]:
        cat = data["category"].lower()
        article.category = cat if cat in KB_CATEGORIES else "general"
    if "tags" in data:
        article.tags = (data["tags"] or "").strip() or None
    if "is_published" in data:
        article.is_published = bool(data["is_published"])
    db.session.commit()
    return article


def delete_article(article_id: int) -> None:
    article = get_article(article_id)
    db.session.delete(article)
    db.session.commit()


def record_view(article_id: int) -> KnowledgeArticle:
    article = get_article(article_id)
    article.view_count = (article.view_count or 0) + 1
    db.session.commit()
    return article


def mark_helpful(article_id: int) -> KnowledgeArticle:
    article = get_article(article_id)
    article.helpful_count = (article.helpful_count or 0) + 1
    db.session.commit()
    return article


def ensure_starter_articles(author_user_id: int | None = None) -> int:
    """Seed starter KB articles if the table is empty."""
    if KnowledgeArticle.query.count():
        return 0
    starters = [
        {
            "title": "How to Fix Outlook",
            "summary": "Profile rebuild, OST repair, and cached mode tips.",
            "category": "email",
            "tags": "outlook,email,office",
            "body": (
                "## Outlook troubleshooting\n\n"
                "1. Confirm network and mailbox access.\n"
                "2. Start Outlook in Safe Mode (`outlook.exe /safe`).\n"
                "3. Rebuild the Outlook profile if needed.\n"
                "4. Repair or recreate the OST cache file.\n"
                "5. Check Cached Exchange Mode settings.\n\n"
                "Escalate to Messaging if Autodiscover fails."
            ),
        },
        {
            "title": "How to Connect VPN",
            "summary": "FortiClient enrollment and common timeout fixes.",
            "category": "vpn",
            "tags": "vpn,remote,forticlient",
            "body": (
                "## VPN connection guide\n\n"
                "1. Install the organizational VPN client from the Software Centre.\n"
                "2. Enroll with your staff email and MFA.\n"
                "3. On timeout: check home internet, then DNS (8.8.8.8 temporarily).\n"
                "4. Re-authenticate MFA if prompted repeatedly.\n"
                "5. Capture exact error text for the ticket.\n"
            ),
        },
        {
            "title": "Printer Offline Guide",
            "summary": "Spooler restart, queue clear, and firmware checks.",
            "category": "printer",
            "tags": "printer,spooler,offline",
            "body": (
                "## Printer offline checklist\n\n"
                "1. Verify power and network cable / Wi-Fi.\n"
                "2. Ping the printer IP from a working PC.\n"
                "3. Restart Print Spooler on the affected workstation.\n"
                "4. Clear stuck jobs in the print queue.\n"
                "5. Check toner/paper and SNMP status in UITOP Printers.\n"
                "6. Link the printer to the ticket for inventory tracking.\n"
            ),
        },
        {
            "title": "Reset MFA",
            "summary": "Self-service and helpdesk MFA reset workflow.",
            "category": "account",
            "tags": "mfa,security,account",
            "body": (
                "## MFA reset workflow\n\n"
                "1. Verify caller identity (staff number / manager confirmation).\n"
                "2. Prefer self-service reset when available.\n"
                "3. Admin reset: revoke old MFA methods, force re-registration.\n"
                "4. Document the request on the ticket with time spent.\n"
                "5. Remind the user never to share OTP codes.\n"
            ),
        },
    ]
    for item in starters:
        create_article(author_user_id=author_user_id, **item)
    return len(starters)
