import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db
from routes.poll_routes import login_required
from services.moderation import CivicModerationService

forum_bp = Blueprint("forum", __name__, url_prefix="/forum")

@forum_bp.route("/")
def forum_index():
    db = get_db()
    poll_filter = request.args.get("poll_id", "All")
    
    query = {"status": "APPROVED"}
    if poll_filter != "All":
        query["poll_id"] = poll_filter
        
    posts = list(db.forum_posts.find(query).sort("created_at", -1))
    polls = list(db.polls.find({"status": "ACTIVE"}, {"poll_id": 1, "title": 1, "slug": 1}))
    
    return render_template(
        "forum.html",
        posts=posts,
        polls=polls,
        selected_poll=poll_filter
    )

@forum_bp.route("/post", methods=["POST"])
@login_required
def create_post():
    content = request.form.get("content", "").strip() or (request.json.get("content", "").strip() if request.is_json else "")
    poll_id = request.form.get("poll_id", "general").strip() or (request.json.get("poll_id", "general") if request.is_json else "general")
    redirect_target = request.form.get("redirect_to")
    
    if not content:
        msg = "Discussion post cannot be empty."
        if request.is_json:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "error")
        return redirect(url_for("forum.forum_index"))
        
    # Evaluate content with Automated Civic Moderation Engine
    mod_result = CivicModerationService.evaluate_text(content)
    
    db = get_db()
    poll_title = "General Civic Policy Discussion"
    if poll_id != "general":
        poll = db.polls.find_one({"$or": [{"poll_id": poll_id}, {"slug": poll_id}]})
        if poll:
            poll_title = poll.get("title", poll_title)
            poll_id = poll.get("poll_id", poll_id)

    post_id = f"post-{secrets.token_hex(6)}"
    post_doc = {
        "post_id": post_id,
        "poll_id": poll_id,
        "poll_title": poll_title,
        "author_hash": session.get("citizen_hash"),
        "author_name": session.get("citizen_name", "Verified Citizen"),
        "content": content,
        "status": mod_result["status"],
        "violations": mod_result["violations"],
        "flagged_terms": mod_result["flagged_keywords"],
        "upvotes": 0,
        "created_at": datetime.now().isoformat()
    }
    
    # Store record
    db.forum_posts.insert_one(post_doc)
    
    if not mod_result["is_approved"]:
        # Content Auto-Removed
        err_msg = f"Post Removed: {mod_result['reason']}"
        if request.is_json:
            return jsonify({
                "success": False,
                "status": "REMOVED",
                "violations": mod_result["violations"],
                "reason": err_msg
            }), 422
            
        flash(err_msg, "error")
        if redirect_target:
            return redirect(redirect_target)
        return redirect(url_for("forum.forum_index"))

    # Content Approved
    success_msg = "Your perspective was verified against civility guidelines and successfully posted."
    if request.is_json:
        return jsonify({
            "success": True,
            "status": "APPROVED",
            "post_id": post_id,
            "message": success_msg
        })
        
    flash(success_msg, "success")
    if redirect_target:
        return redirect(redirect_target)
    return redirect(url_for("forum.forum_index"))

@forum_bp.route("/<post_id>/upvote", methods=["POST"])
@login_required
def upvote_post(post_id):
    db = get_db()
    db.forum_posts.update_one({"post_id": post_id}, {"$inc": {"upvotes": 1}})
    updated = db.forum_posts.find_one({"post_id": post_id})
    upvotes = updated.get("upvotes", 0) if updated else 0
    
    if request.is_json:
        return jsonify({"success": True, "upvotes": upvotes})
    return redirect(url_for("forum.forum_index"))

@forum_bp.route("/<post_id>/report", methods=["POST"])
@login_required
def report_post(post_id):
    db = get_db()
    reason = request.form.get("reason", "Violates respectful discourse guidelines.")
    db.forum_posts.update_one(
        {"post_id": post_id},
        {"$set": {"status": "FLAGGED_REVIEW", "report_reason": reason}}
    )
    flash("Thank you for maintaining community decency. This post has been submitted for immediate audit.", "info")
    return redirect(url_for("forum.forum_index"))
