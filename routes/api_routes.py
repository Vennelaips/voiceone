import secrets
from datetime import datetime
from flask import Blueprint, request, jsonify
from database import get_db
from services.crypto import hash_aadhaar, is_eligible_citizen, sanitize_aadhaar, is_valid_aadhaar_format
from services.moderation import CivicModerationService

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "HEALTHY",
        "service": "VoiceOne Civic Backend",
        "timestamp": datetime.now().isoformat(),
        "database": "CONNECTED"
    })

@api_bp.route("/auth/verify", methods=["POST"])
def api_auth_verify():
    data = request.get_json(silent=True) or request.form
    name = data.get("name", "").strip()
    aadhaar_raw = data.get("aadhaar", "").strip()
    dob = data.get("dob", "").strip()

    if not name or not aadhaar_raw or not dob:
        return jsonify({
            "success": False,
            "error": "Missing required fields: name, aadhaar, and dob (YYYY-MM-DD)."
        }), 400

    clean_aadhaar = sanitize_aadhaar(aadhaar_raw)
    if not is_valid_aadhaar_format(clean_aadhaar):
        return jsonify({
            "success": False,
            "error": "Invalid Aadhaar format. Must be a 12-digit numeric identifier."
        }), 400

    is_eligible, age, msg = is_eligible_citizen(dob)
    if not is_eligible:
        return jsonify({
            "success": False,
            "error": msg,
            "age": age,
            "eligible": False
        }), 403

    citizen_hash = hash_aadhaar(clean_aadhaar)
    db = get_db()
    db.users.update_one(
        {"citizen_hash": citizen_hash},
        {
            "$set": {
                "name": name,
                "age": age,
                "digilocker_verified": True,
                "last_active": datetime.now().isoformat()
            },
            "$setOnInsert": {
                "citizen_hash": citizen_hash,
                "created_at": datetime.now().isoformat(),
                "total_votes_cast": 0
            }
        },
        upsert=True
    )

    return jsonify({
        "success": True,
        "message": "Citizen identity authenticated via DigiLocker.",
        "citizen_hash": citizen_hash,
        "name": name,
        "age": age,
        "digilocker_verified": True
    })

@api_bp.route("/polls", methods=["GET"])
def api_get_polls():
    db = get_db()
    polls = list(db.polls.find({"status": "ACTIVE"}, {"_id": 0}).sort("created_at", -1))
    return jsonify({
        "success": True,
        "count": len(polls),
        "polls": polls
    })

@api_bp.route("/polls", methods=["POST"])
def api_create_poll():
    data = request.get_json(silent=True) or request.form
    title = data.get("title", "").strip()
    summary = data.get("summary", "").strip()
    source_url = data.get("official_source_url", "").strip()
    category = data.get("category", "General Policy")
    bill_number = data.get("bill_number", "Public Action 2026")
    citizen_hash = data.get("citizen_hash", "citizen_v_api_author")

    if not title or not summary or not source_url:
        return jsonify({
            "success": False,
            "error": "title, summary, and official_source_url are required."
        }), 400

    poll_id = f"poll-{secrets.token_hex(6)}"
    slug = f"bill-{secrets.token_hex(4)}"

    db = get_db()
    new_poll = {
        "poll_id": poll_id,
        "slug": slug,
        "title": title,
        "bill_number": bill_number,
        "category": category,
        "summary": summary,
        "official_source_url": source_url,
        "fact_check_notes": data.get("fact_check_notes", "Verified source referenced."),
        "created_by": citizen_hash,
        "created_by_name": data.get("author_name", "Verified Citizen"),
        "status": "ACTIVE",
        "created_at": datetime.now().isoformat(),
        "votes_for": 0,
        "votes_against": 0,
        "voters": {}
    }
    db.polls.insert_one(new_poll)

    return jsonify({
        "success": True,
        "message": "Civic poll created successfully.",
        "poll_id": poll_id,
        "poll": {k: v for k, v in new_poll.items() if k != "_id"}
    }), 201

@api_bp.route("/polls/<poll_id>", methods=["GET"])
def api_get_poll_detail(poll_id):
    db = get_db()
    poll = db.polls.find_one({"$or": [{"poll_id": poll_id}, {"slug": poll_id}]}, {"_id": 0})
    if not poll:
        return jsonify({"success": False, "error": "Poll not found."}), 404
    return jsonify({"success": True, "poll": poll})

@api_bp.route("/polls/<poll_id>/vote", methods=["POST"])
def api_vote(poll_id):
    data = request.get_json(silent=True) or request.form
    choice = data.get("choice", "").upper()
    citizen_hash = data.get("citizen_hash", "").strip()

    if choice not in ("FOR", "AGAINST"):
        return jsonify({"success": False, "error": "Choice must be 'FOR' or 'AGAINST'."}), 400
    if not citizen_hash:
        return jsonify({"success": False, "error": "citizen_hash is required to record a verified vote."}), 400

    db = get_db()
    poll = db.polls.find_one({"$or": [{"poll_id": poll_id}, {"slug": poll_id}]})
    if not poll:
        return jsonify({"success": False, "error": "Poll not found."}), 404

    voters = poll.get("voters", {})
    prev_vote = voters.get(citizen_hash)
    inc_for = 0
    inc_against = 0

    if prev_vote == choice:
        msg = f"Vote already recorded as {choice}."
    elif prev_vote is None:
        if choice == "FOR":
            inc_for = 1
        else:
            inc_against = 1
        msg = f"Vote '{choice}' recorded successfully."
        db.users.update_one({"citizen_hash": citizen_hash}, {"$inc": {"total_votes_cast": 1}})
    else:
        if choice == "FOR":
            inc_for = 1
            inc_against = -1
        else:
            inc_for = -1
            inc_against = 1
        msg = f"Vote updated to '{choice}'."

    update_query = {"$set": {f"voters.{citizen_hash}": choice}}
    if inc_for != 0 or inc_against != 0:
        update_query["$inc"] = {}
        if inc_for != 0:
            update_query["$inc"]["votes_for"] = inc_for
        if inc_against != 0:
            update_query["$inc"]["votes_against"] = inc_against

    db.polls.update_one({"poll_id": poll["poll_id"]}, update_query)
    updated = db.polls.find_one({"poll_id": poll["poll_id"]}, {"_id": 0})

    return jsonify({
        "success": True,
        "message": msg,
        "poll_id": poll["poll_id"],
        "votes_for": updated.get("votes_for", 0),
        "votes_against": updated.get("votes_against", 0)
    })

@api_bp.route("/forum", methods=["GET"])
def api_get_forum():
    db = get_db()
    posts = list(db.forum_posts.find({"status": "APPROVED"}, {"_id": 0}).sort("created_at", -1))
    return jsonify({
        "success": True,
        "count": len(posts),
        "posts": posts
    })

@api_bp.route("/forum/post", methods=["POST"])
def api_create_forum_post():
    data = request.get_json(silent=True) or request.form
    content = data.get("content", "").strip()
    citizen_hash = data.get("citizen_hash", "citizen_v_api_user")
    author_name = data.get("author_name", "Verified Citizen")
    poll_id = data.get("poll_id", "general")

    if not content:
        return jsonify({"success": False, "error": "Content cannot be empty."}), 400

    mod_result = CivicModerationService.evaluate_text(content)
    post_id = f"post-{secrets.token_hex(6)}"

    db = get_db()
    post_doc = {
        "post_id": post_id,
        "poll_id": poll_id,
        "author_hash": citizen_hash,
        "author_name": author_name,
        "content": content,
        "status": mod_result["status"],
        "violations": mod_result["violations"],
        "flagged_terms": mod_result["flagged_keywords"],
        "upvotes": 0,
        "created_at": datetime.now().isoformat()
    }
    db.forum_posts.insert_one(post_doc)

    if not mod_result["is_approved"]:
        return jsonify({
            "success": False,
            "status": "REMOVED",
            "reason": mod_result["reason"],
            "violations": mod_result["violations"]
        }), 422

    return jsonify({
        "success": True,
        "status": "APPROVED",
        "post_id": post_id,
        "message": "Discussion post verified and published."
    }), 201
