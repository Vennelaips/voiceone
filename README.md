# VoiceOne 🗳️ — Secure & Privacy-Preserving Civic Polling

**VoiceOne** is a sovereign civic polling and discussion platform enabling citizens to express verified opinions on legislative bills, national laws, and societal policies. Authenticated via **DigiLocker OAuth 2.0**, citizens are verified to be 18+ years of age, while their **Aadhaar numbers are never stored in plaintext**—they are cryptographically salted and hashed into unique anonymous voter identifiers.

---

## 🎨 Visual Identity & Design System
- **Backdrop**: Sage Green (`#87AE73`)
- **Icons, Headings & Primary Accents**: Amaranth Pink (`#9F2B68`)
- **Panels & Ballots**: Tactile **E-Ink / Cream Paper Panels** (`#FAF7F2`) with crisp editorial borders and ink shadows (`box-shadow: 4px 4px 0px rgba(159, 43, 104, 0.35)`).
- **Typography**: Google Fonts (*Outfit* and *Plus Jakarta Sans*).

---
## Architecture & System Design
```
+-------------------------------------------------------------------------+
|                              VoiceOne UI                                |
|  Theme: Sage Green (#87AE73) Backdrop + Amaranth Pink (#9F2B68) Accents |
+------------------------------------+------------------------------------+
                                     |
                RESTful / Form Requests & AJAX Polling
                                     |
+------------------------------------v------------------------------------+
|                         Flask Application Core                          |
|                                                                         |
|  +------------------------+  +--------------------+  +---------------+  |
|  | DigiLocker OAuth2 /    |  | Verified Bill /    |  | Anti-Hate /   |  |
|  | Cryptographic Hashing  |  | Binary Polling     |  | Civic Forum   |  |
|  | (18+ Age Verification) |  | (For vs Against)   |  | Moderation    |  |
|  +------------------------+  +--------------------+  +---------------+  |
+------------------------------------+------------------------------------+
                                     |
              PyMongo / MongoMock Persistence Layer
                                     |
+------------------------------------v------------------------------------+
|                             MongoDB Data                                |
|    - Users (Citizen Hash, Age Verified, DigiLocker Auth Token)          |
|    - Polls (Bill Title, Gazette/Fact-Check Link, Votes: For / Against)  |
|    - ForumPosts (Author Hash, Content, Civility Status, Mod Flags)      |
+-------------------------------------------------------------------------+

```

## 🏛️ System Architecture & Workflow Diagram

```mermaid
flowchart TB
    subgraph ClientLayer["🖥️ Frontend & Citizen UI (E-Ink Paper / Sage & Amaranth)"]
        UI_Login["Citizen Login Form<br/>(Name, Aadhaar, DOB)"]
        UI_Bills["Active Bills & Law Feed<br/>(Binary Voting: FOR / AGAINST)"]
        UI_Forum["Civic Discussion Forum<br/>(Polite, Respectful Perspectives)"]
        UI_Create["Propose Researched Bill<br/>(Official Gazette / Fact-Check Link)"]
    end

    subgraph SecurityLayer["🛡️ Identity & Privacy-Preserving Engine"]
        AgeCheck{"Age Verification<br/>(Calculated Age >= 18?)"}
        AgeReject["❌ Denied (403 Forbidden)<br/>Must be 18+ to vote"]
        HMAC["🔐 Salted HMAC-SHA256<br/>Zero-Knowledge Aadhaar Hashing"]
        AnonVoter["Citizen Pseudonym Generated<br/>(citizen_v_...)<br/>⚡ Raw Aadhaar Immediately Discarded"]
        DigiOAuth["🏛️ DigiLocker OAuth 2.0 Gateway<br/>(Token & KYC Authentication)"]
    end

    subgraph BackendCore["⚙️ VoiceOne Flask Backend Services"]
        AuthService["Auth & Session Controller<br/>(routes/auth_routes.py)"]
        PollService["Verified Bill & Voting Engine<br/>(routes/poll_routes.py)<br/>• Atomic Deduplication (1 Voter = 1 Vote)<br/>• Real-Time Asynchronous Tallying"]
        ModEngine["Civic Moderation Engine<br/>(services/moderation.py)<br/>• Scans Caste, Class, Religion, Gender & Orientation<br/>• Auto-Removes Violations"]
        APIService["RESTful API Endpoints<br/>(routes/api_routes.py)"]
    end

    subgraph DatabaseLayer["🗄️ Persistence Layer (MongoDB / MongoMock Dual Mode)"]
        DB_Users[("Users Collection<br/>• Citizen Hash<br/>• Age (18+ Verified)<br/>• Total Votes")]
        DB_Polls[("Polls Collection<br/>• Bill Title & Gazette URL<br/>• Votes: For / Against<br/>• Voter Fingerprints")]
        DB_Forum[("Forum Posts Collection<br/>• Author Hash<br/>• Approved Content<br/>• Timestamp & Upvotes")]
    end

    %% Flow connections
    UI_Login -->|"Submit Credentials"| AgeCheck
    AgeCheck -->|"Age < 18"| AgeReject
    AgeCheck -->|"Age >= 18"| HMAC
    HMAC --> AnonVoter
    AnonVoter --> AuthService
    UI_Login <-->|"OAuth 2.0 Handshake"| DigiOAuth
    DigiOAuth --> AuthService
    
    AuthService --> DB_Users
    
    UI_Bills -->|"Cast / Toggle Vote"| PollService
    UI_Create -->|"Submit Researched Bill"| PollService
    PollService --> DB_Polls
    
    UI_Forum -->|"Post Perspective"| ModEngine
    ModEngine -->|"Approved"| DB_Forum
    ModEngine -->|"Violation Detected"| UI_Forum
    
    APIService <-->|"Postman / Automated Suite"| BackendCore
```

---

## 🛡️ Core Security & Architectural Features

1. **DigiLocker OAuth 2.0 & Salted Aadhaar Anonymization**:
   - Accepts Name, 12-digit Aadhaar, and Date of Birth (DOB).
   - Strict Age Eligibility: Under-18 users are rejected.
   - **Zero Plaintext Storage**: Plaintext Aadhaar is never saved in the database or server logs. It is instantly transformed into a cryptographically salted one-way hash (`SHA-256` / `HMAC-SHA256`) acting as a secure voter pseudonym to enforce one-citizen-one-vote while preserving privacy.
2. **Verified Legislative Bills & Binary Voting**:
   - Poll creation requires reference to official gazette notices or fact-checked sources.
   - Strict binary voting: **FOR** (Support) or **AGAINST** (Oppose).
   - Real-time percentage calculation with zero latency.
3. **Automated Civic Moderation Engine**:
   - Real-time civility scanning enforcing polite discourse.
   - Prohibits discrimination based on **caste, class, religion, sexual orientation, or gender**, as well as profanity and harassment. Violations are **automatically removed**.
4. **Resilient Dual-Mode Database**:
   - Native support for live MongoDB (Local or MongoDB Atlas) with an automatic embedded in-memory fallback (`mongomock`) for zero-configuration testing and continuous integration.

---

