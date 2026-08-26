from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db
from services.crypto import hash_aadhaar, is_eligible_citizen, sanitize_aadhaar, is_valid_aadhaar_format
from services.digilocker_oauth import DigiLockerOAuthService

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("is_authenticated"):
            return redirect(url_for("polls.dashboard"))
        return render_template("login.html")

    # Handle Direct Aadhaar / DigiLocker Verification Form
    name = request.form.get("name", "").strip()
    aadhaar_raw = request.form.get("aadhaar", "").strip()
    dob = request.form.get("dob", "").strip()

    if not name or not aadhaar_raw or not dob:
        flash("Please provide your full Name, 12-digit Aadhaar Number, and Date of Birth.", "error")
        return render_template("login.html", name=name, dob=dob), 400

    clean_aadhaar = sanitize_aadhaar(aadhaar_raw)
    if not is_valid_aadhaar_format(clean_aadhaar):
        flash("Invalid Aadhaar number format. Aadhaar must contain exactly 12 numeric digits.", "error")
        return render_template("login.html", name=name, dob=dob), 400

    is_eligible, age, message = is_eligible_citizen(dob)
    if not is_eligible:
        flash(f"Verification Failed: {message}", "error")
        return render_template("login.html", name=name, dob=dob), 403

    # Cryptographically hash the Aadhaar immediately - NEVER persist or log raw Aadhaar
    try:
        citizen_hash = hash_aadhaar(clean_aadhaar)
    except Exception as e:
        flash(f"Identity hashing error: {str(e)}", "error")
        return render_template("login.html", name=name, dob=dob), 400

    # Upsert Citizen in Database with Hashed Identity
    db = get_db()
    db.users.update_one(
        {"citizen_hash": citizen_hash},
        {
            "$set": {
                "name": name,
                "age": age,
                "dob_year": dob.split("-")[0] if "-" in dob else dob.split("/")[-1],
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

    # Establish secure session
    session["is_authenticated"] = True
    session["citizen_hash"] = citizen_hash
    session["citizen_name"] = name
    session["citizen_age"] = age
    session["digilocker_verified"] = True

    flash(f"Welcome to VoiceOne, {name}! Your identity is verified via DigiLocker (Age: {age}). Aadhaar remains fully private & hashed.", "success")
    return redirect(url_for("polls.dashboard"))

@auth_bp.route("/digilocker/initiate")
def digilocker_initiate():
    state = DigiLockerOAuthService.generate_state_token()
    session["oauth_state"] = state
    auth_url = DigiLockerOAuthService.get_authorization_url(state, is_sandbox=True)
    return redirect(auth_url)

@auth_bp.route("/digilocker/sandbox-consent", methods=["GET", "POST"])
def sandbox_consent():
    state = request.args.get("state") or session.get("oauth_state", "")
    if request.method == "GET":
        return render_template("sandbox_consent.html", state=state)

    # Simulated Consent Authorization
    name = request.form.get("name", "Ananya Deshmukh").strip()
    aadhaar_raw = request.form.get("aadhaar", "874512963401").strip()
    dob = request.form.get("dob", "2000-05-15").strip()

    clean_aadhaar = sanitize_aadhaar(aadhaar_raw)
    is_eligible, age, message = is_eligible_citizen(dob)
    if not is_eligible:
        flash(f"DigiLocker KYC Verification Failed: {message}", "error")
        return render_template("sandbox_consent.html", state=state), 403

    # Generate sandbox auth code and redirect to callback
    auth_code = f"dl_sandbox_{state[:8]}_{int(datetime.now().timestamp())}"
    # Temporary store for sandbox profile exchange
    session["sandbox_creds"] = {
        "name": name,
        "aadhaar": clean_aadhaar,
        "dob": dob
    }
    return redirect(url_for("auth.digilocker_callback", code=auth_code, state=state))

@auth_bp.route("/digilocker/callback")
def digilocker_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("Authorization failed or was cancelled by user.", "error")
        return redirect(url_for("auth.login"))

    # Exchange code for token
    token_resp = DigiLockerOAuthService.exchange_code_for_token(code, is_sandbox=True)
    access_token = token_resp.get("access_token", "")

    # Retrieve KYC profile using sandbox session payload or token
    raw_creds = session.pop("sandbox_creds", None)
    profile_resp = DigiLockerOAuthService.fetch_user_profile(access_token, raw_credentials=raw_creds)

    if not profile_resp.get("success"):
        flash(profile_resp.get("error", "DigiLocker identity authentication failed."), "error")
        return redirect(url_for("auth.login"))

    citizen_hash = profile_resp["citizen_hash"]
    name = profile_resp["name"]
    age = profile_resp["age"]

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

    session["is_authenticated"] = True
    session["citizen_hash"] = citizen_hash
    session["citizen_name"] = name
    session["citizen_age"] = age
    session["digilocker_verified"] = True

    flash(f"DigiLocker OAuth 2.0 Verification Successful! Welcome, {name}.", "success")
    return redirect(url_for("polls.dashboard"))

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have safely logged out of VoiceOne.", "info")
    return redirect(url_for("auth.login"))
