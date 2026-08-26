import re
import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db

poll_bp = Blueprint("polls", __name__)

def login_required(func):
    """Decorator to enforce authenticated session."""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("is_authenticated"):
            flash("Please authenticate your identity via DigiLocker to participate in civic polls.", "warning")
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)
    return wrapper

@poll_bp.route("/")
@poll_bp.route("/polls")
def dashboard():
    db = get_db()
    category = request.args.get("category", "All")
    query = request.args.get("q", "").strip()

    filter_criteria = {"status": "ACTIVE"}
    if category != "All":
        filter_criteria["category"] = category
    if query:
        filter_criteria["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"summary": {"$regex": query, "$options": "i"}},
            {"bill_number": {"$regex": query, "$options": "i"}}
        ]

    polls = list(db.polls.find(filter_criteria).sort("created_at", -1))
    current_user_hash = session.get("citizen_hash")

    # Compute percentage stats and user vote for each poll
    for poll in polls:
        voters = poll.get("voters", {})
        votes_for = poll.get("votes_for", 0)
        votes_against = poll.get("votes_against", 0)
        total_votes = votes_for + votes_against
        
        poll["total_votes"] = total_votes
        poll["pct_for"] = round((votes_for / total_votes * 100), 1) if total_votes > 0 else 0.0
        poll["pct_against"] = round((votes_against / total_votes * 100), 1) if total_votes > 0 else 0.0
        poll["user_vote"] = voters.get(current_user_hash) if current_user_hash else None

    # Categories list
    categories = ["All", "Technology & Privacy", "Environment & Energy", "Labor & Economy", "Healthcare & Welfare", "Education & Rights", "Constitutional Law"]

    return render_template(
        "dashboard.html",
        polls=polls,
        selected_category=category,
        categories=categories,
        search_query=query
    )

@poll_bp.route("/polls/create", methods=["GET", "POST"])
@login_required
def create_poll():
    if request.method == "GET":
        return render_template("create_poll.html")

    title = request.form.get("title", "").strip()
    bill_number = request.form.get("bill_number", "").strip()
    category = request.form.get("category", "").strip()
    summary = request.form.get("summary", "").strip()
    official_source_url = request.form.get("official_source_url", "").strip()
    fact_check_notes = request.form.get("fact_check_notes", "").strip()

    if not title or not summary or not official_source_url:
        flash("Title, Summary, and Official Research Source URL are required to publish a civic poll.", "error")
        return render_template("create_poll.html", form_data=request.form), 400

    # Ensure URL is valid
    if not (official_source_url.startswith("http://") or official_source_url.startswith("https://")):
        flash("Please provide a valid web URL (e.g. https://prsindia.org/...) for the source.", "error")
        return render_template("create_poll.html", form_data=request.form), 400

    # Generate slug and poll_id
    clean_slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", clean_slug).strip("-")[:60] or f"bill-{secrets.token_hex(4)}"
    poll_id = f"poll-{secrets.token_hex(6)}"

    db = get_db()
    new_poll = {
        "poll_id": poll_id,
        "slug": slug,
        "title": title,
        "bill_number": bill_number or "Public Policy Action",
        "category": category or "General Public Law",
        "summary": summary,
        "official_source_url": official_source_url,
        "fact_check_notes": fact_check_notes or "Submitted by verified citizen voter.",
        "created_by": session.get("citizen_hash"),
        "created_by_name": session.get("citizen_name", "Verified Citizen"),
        "status": "ACTIVE",
        "created_at": datetime.now().isoformat(),
        "votes_for": 0,
        "votes_against": 0,
        "voters": {}
    }

    db.polls.insert_one(new_poll)
    flash(f"Civic Poll '{title}' successfully created and open for nationwide voting.", "success")
    return redirect(url_for("polls.poll_detail", poll_id=poll_id))

@poll_bp.route("/polls/<poll_id>")
def poll_detail(poll_id):
    db = get_db()
    poll = db.polls.find_one({"$or": [{"poll_id": poll_id}, {"slug": poll_id}]})
    if not poll:
        flash("Requested civic poll could not be found.", "error")
        return redirect(url_for("polls.dashboard"))

    current_user_hash = session.get("citizen_hash")
    voters = poll.get("voters", {})
    votes_for = poll.get("votes_for", 0)
    votes_against = poll.get("votes_against", 0)
    total_votes = votes_for + votes_against
    
    poll["total_votes"] = total_votes
    poll["pct_for"] = round((votes_for / total_votes * 100), 1) if total_votes > 0 else 0.0
    poll["pct_against"] = round((votes_against / total_votes * 100), 1) if total_votes > 0 else 0.0
    poll["user_vote"] = voters.get(current_user_hash) if current_user_hash else None

    # Load linked forum discussions for this specific poll
    discussions = list(db.forum_posts.find({"poll_id": poll["poll_id"], "status": "APPROVED"}).sort("created_at", -1))

    return render_template("poll_detail.html", poll=poll, discussions=discussions)

@poll_bp.route("/polls/<poll_id>/vote", methods=["POST"])
@login_required
def cast_vote(poll_id):
    choice = request.form.get("choice") or (request.json.get("choice") if request.is_json else None)
    if choice not in ("FOR", "AGAINST"):
        if request.is_json:
            return jsonify({"success": False, "error": "Invalid vote choice. Must be 'FOR' or 'AGAINST'."}), 400
        flash("Invalid voting selection.", "error")
        return redirect(url_for("polls.poll_detail", poll_id=poll_id))

    db = get_db()
    poll = db.polls.find_one({"$or": [{"poll_id": poll_id}, {"slug": poll_id}]})
    if not poll:
        if request.is_json:
            return jsonify({"success": False, "error": "Poll not found."}), 404
        flash("Poll not found.", "error")
        return redirect(url_for("polls.dashboard"))

    citizen_hash = session.get("citizen_hash")
    voters = poll.get("voters", {})
    prev_vote = voters.get(citizen_hash)

    # Calculate vote delta
    inc_for = 0
    inc_against = 0

    if prev_vote == choice:
        # Already voted the same
        msg = f"You have already voted {choice} on this bill."
    elif prev_vote is None:
        # New voter
        if choice == "FOR":
            inc_for = 1
        else:
            inc_against = 1
        msg = f"Your vote '{choice}' has been securely recorded."
        # Update user total votes
        db.users.update_one({"citizen_hash": citizen_hash}, {"$inc": {"total_votes_cast": 1}})
    else:
        # Changed vote
        if choice == "FOR":
            inc_for = 1
            inc_against = -1
        else:
            inc_for = -1
            inc_against = 1
        msg = f"Your vote changed to '{choice}'."

    # Atomic update on poll document
    update_query = {
        "$set": {f"voters.{citizen_hash}": choice}
    }
    if inc_for != 0 or inc_against != 0:
        update_query["$inc"] = {}
        if inc_for != 0:
            update_query["$inc"]["votes_for"] = inc_for
        if inc_against != 0:
            update_query["$inc"]["votes_against"] = inc_against

    db.polls.update_one({"poll_id": poll["poll_id"]}, update_query)

    # Fetch updated numbers
    updated_poll = db.polls.find_one({"poll_id": poll["poll_id"]})
    v_for = updated_poll.get("votes_for", 0)
    v_against = updated_poll.get("votes_against", 0)
    tot = v_for + v_against
    pct_for = round((v_for / tot * 100), 1) if tot > 0 else 0.0
    pct_against = round((v_against / tot * 100), 1) if tot > 0 else 0.0

    if request.is_json:
        return jsonify({
            "success": True,
            "message": msg,
            "choice": choice,
            "votes_for": v_for,
            "votes_against": v_against,
            "total_votes": tot,
            "pct_for": pct_for,
            "pct_against": pct_against
        })

    flash(msg, "success")
    return redirect(url_for("polls.poll_detail", poll_id=poll["poll_id"]))
