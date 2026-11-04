"""Routes for IT Copilot (AI assistant)."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request, session

from uitop.extensions import db
from uitop.models.copilot import CopilotMessage, CopilotSession
from uitop.services.copilot import ask_copilot, classify_intent, gather_context

bp = Blueprint("ai", __name__, url_prefix="/ai")


def _current_user_id() -> int | None:
    return session.get("user_id")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@bp.get("/")
def index():
    user_id = _current_user_id()
    sessions = []
    if user_id:
        sessions = (
            CopilotSession.query.filter_by(user_id=user_id)
            .order_by(CopilotSession.updated_at.desc())
            .limit(20)
            .all()
        )

    snapshot = {}
    try:
        from uitop.services.copilot import _ctx_dashboard

        snapshot = _ctx_dashboard() or {}
    except Exception:
        snapshot = {}

    return render_template(
        "ai/index.html",
        active="ai",
        copilot_sessions=sessions,
        snapshot=snapshot,
    )


@bp.get("/<int:item_id>/history")
def history(item_id: int):
    s = CopilotSession.query.get_or_404(item_id)
    if s.user_id != _current_user_id():
        return jsonify({"error": "Forbidden"}), 403
    return render_template("ai/history.html", active="ai", copilot_session=s)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@bp.post("/ask")
def ask():
    """Main copilot endpoint.

    JSON body:
        question  (str)  — required
        session_id (int) — optional, resumes a session
    """
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400

    # Session management
    session_id = data.get("session_id")
    copilot_session = None
    if session_id:
        copilot_session = CopilotSession.query.filter_by(id=session_id, user_id=user_id).first()

    if not copilot_session:
        copilot_session = CopilotSession(
            user_id=user_id,
            title=question[:80],
        )
        db.session.add(copilot_session)
        db.session.flush()  # get id

    history = copilot_session.history()

    # Classify intent and gather DB context
    intents = classify_intent(question)
    context = gather_context(question, intents)

    # Get AI answer
    answer = ask_copilot(question, history, context)

    # Persist messages
    db.session.add(CopilotMessage(
        session_id=copilot_session.id,
        role="user",
        content=question,
    ))
    db.session.add(CopilotMessage(
        session_id=copilot_session.id,
        role="assistant",
        content=answer,
        context_snapshot=context,
    ))
    db.session.commit()

    return jsonify({
        "answer": answer,
        "session_id": copilot_session.id,
        "intents": intents,
    })


@bp.get("/sessions")
def sessions():
    """Return recent sessions for the current user (JSON)."""
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    rows = (
        CopilotSession.query.filter_by(user_id=user_id)
        .order_by(CopilotSession.updated_at.desc())
        .limit(20)
        .all()
    )
    return jsonify([
        {"id": s.id, "title": s.title, "updated_at": s.updated_at.isoformat()}
        for s in rows
    ])


@bp.get("/sessions/<int:session_id>/messages")
def session_messages(session_id: int):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    s = CopilotSession.query.filter_by(id=session_id, user_id=user_id).first_or_404()
    return jsonify([
        {"role": m.role, "content": m.content, "at": m.created_at.isoformat()}
        for m in s.messages
    ])
