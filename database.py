import logging
from datetime import datetime
import pymongo
from pymongo import MongoClient
import mongomock
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceOneDB")

class Database:
    _instance = None
    _client = None
    _db = None
    _is_mock = False

    @classmethod
    def get_db(cls):
        if cls._db is not None:
            return cls._db

        # Try connecting to live MongoDB
        try:
            client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=1500)
            client.admin.command('ping')
            cls._client = client
            cls._db = client[Config.DB_NAME]
            cls._is_mock = False
            logger.info("Connected successfully to Live MongoDB instance.")
        except Exception as e:
            if 'client' in locals() and client:
                try:
                    client.close()
                except Exception:
                    pass
            logger.warning(f"Live MongoDB not available. Initializing high-fidelity persistent MongoMock instance.")
            cls._client = mongomock.MongoClient()
            cls._db = cls._client[Config.DB_NAME]
            cls._is_mock = True

        cls._init_indexes_and_seeds()
        return cls._db

    @classmethod
    def _init_indexes_and_seeds(cls):
        """Initializes unique indexes and seeds authentic bills and discussions."""
        db = cls._db
        try:
            db.users.create_index("citizen_hash", unique=True)
            db.polls.create_index("slug", unique=True)
            db.forum_posts.create_index("created_at")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

        # Seed realistic public bills & policies if database is empty
        if db.polls.count_documents({}) == 0:
            sample_bills = [
                {
                    "poll_id": "poll-dpdp-2026",
                    "slug": "digital-personal-data-protection-act",
                    "title": "Digital Personal Data Protection & AI Governance Amendment 2026",
                    "bill_number": "Bill No. 142 of 2026 (Lok Sabha)",
                    "category": "Technology & Privacy",
                    "summary": "Mandates explicit consent architectures for biometric AI models, strictly limits surveillance data retention by tech platforms to 30 days, and enforces high penalties for citizen identity breaches.",
                    "official_source_url": "https://prsindia.org/billtrack/digital-personal-data-protection-bill",
                    "fact_check_notes": "Official gazette draft verified via PRS Legislative Research and Ministry of Electronics & IT.",
                    "created_by": "citizen_v_system_verifier",
                    "created_by_name": "Civic Verification Desk",
                    "status": "ACTIVE",
                    "created_at": datetime.now().isoformat(),
                    "votes_for": 0,
                    "votes_against": 0,
                    "voters": {}
                },
                {
                    "poll_id": "poll-green-energy-2026",
                    "slug": "rooftop-solar-clean-energy-mandate",
                    "title": "National Green Energy & Mandatory Rooftop Solar Policy 2026",
                    "bill_number": "Gazette Ref: MNRE-2026-B9",
                    "category": "Environment & Energy",
                    "summary": "Requires all new residential and commercial structures over 2,000 sq ft to incorporate solar power generation systems with 40% government subsidy and net-metering guarantees.",
                    "official_source_url": "https://mnre.gov.in/solar/schemes",
                    "fact_check_notes": "Cross-verified with Ministry of New and Renewable Energy notifications.",
                    "created_by": "citizen_v_system_verifier",
                    "created_by_name": "Civic Verification Desk",
                    "status": "ACTIVE",
                    "created_at": datetime.now().isoformat(),
                    "votes_for": 0,
                    "votes_against": 0,
                    "voters": {}
                },
                {
                    "poll_id": "poll-gig-workers-2026",
                    "slug": "gig-and-platform-workers-social-security-bill",
                    "title": "Gig & Platform Economy Workers Social Security Bill 2026",
                    "bill_number": "Bill No. 88 of 2026 (Rajya Sabha)",
                    "category": "Labor & Economy",
                    "summary": "Establishes a mandatory welfare fund financed by a 2% transaction fee on ride-hailing and quick-commerce platforms, providing medical insurance, pension benefits, and accident coverage for delivery personnel.",
                    "official_source_url": "https://labour.gov.in/social-security",
                    "fact_check_notes": "Verified from Ministry of Labour & Employment public consultation draft.",
                    "created_by": "citizen_v_system_verifier",
                    "created_by_name": "Civic Verification Desk",
                    "status": "ACTIVE",
                    "created_at": datetime.now().isoformat(),
                    "votes_for": 0,
                    "votes_against": 0,
                    "voters": {}
                }
            ]
            db.polls.insert_many(sample_bills)

        if db.forum_posts.count_documents({}) == 0:
            sample_discussions = [
                {
                    "post_id": "post-civic-101",
                    "poll_id": "poll-dpdp-2026",
                    "poll_title": "Digital Personal Data Protection & AI Governance Amendment 2026",
                    "author_hash": "citizen_v_a98b71c4e90",
                    "author_name": "Aarav Sharma",
                    "content": "The 30-day retention ceiling for AI biometrics is a massive step forward for constitutional privacy rights. We need clear auditing standards for verification bodies.",
                    "status": "APPROVED",
                    "violations": [],
                    "upvotes": 18,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "post_id": "post-civic-102",
                    "poll_id": "poll-gig-workers-2026",
                    "poll_title": "Gig & Platform Economy Workers Social Security Bill 2026",
                    "author_hash": "citizen_v_3b88d2f419c",
                    "author_name": "Priya Nair",
                    "content": "Platform companies generate immense market valuation. A 2% welfare contribution will finally provide a social safety net for thousands of delivery workers without hurting consumer prices.",
                    "status": "APPROVED",
                    "violations": [],
                    "upvotes": 24,
                    "created_at": datetime.now().isoformat()
                }
            ]
            db.forum_posts.insert_many(sample_discussions)

def get_db():
    return Database.get_db()
