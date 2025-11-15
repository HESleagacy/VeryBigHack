from pymongo.database import Database
from datetime import datetime, timedelta, timezone
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.blockchain import log_threat_to_blockchain
# Load the sentence transformer model once
print("Scoring: Loading sentence-transformer model...")
similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Scoring: Sentence-transformer model loaded.")

def calculate_v_score(query_logs: list) -> float:
    """Calculates Velocity Score (V-Score)."""
    if not query_logs:
        return 0.0
    
    query_count = len(query_logs)
    if query_count > 50: # Hard cap
        return 1.0
    
    # Simple linear scale: 50 queries in 5 min = 1.0 score
    return min(query_count / 50.0, 1.0)

def calculate_d_score(query_logs: list) -> float:
    """Calculates Similarity/Distance Score (D-Score)."""
    if len(query_logs) < 5: # Need at least 5 prompts to compare
        return 0.0

    prompts = [log['prompt'] for log in query_logs]
    embeddings = similarity_model.encode(prompts)
    
    # Calculate pairwise cosine similarity
    sim_matrix = cosine_similarity(embeddings)
    
    # Get the average of the upper triangle (to avoid self-comparison)
    upper_tri_indices = np.triu_indices_from(sim_matrix, k=1)
    if upper_tri_indices[0].size == 0:
        return 0.0
        
    avg_similarity = np.mean(sim_matrix[upper_tri_indices])
    
    # High similarity is suspicious
    return float(avg_similarity)

def run_analysis_job(db: Database):
    """
    The main analysis job called by the scheduler.
    """
    print(f"\n[Analysis Job] Running at {datetime.now(timezone.utc)}...")
    users_collection = db["users"]
    query_logs_collection = db["query_logs"]

    # Get users we need to analyze (e.g., active in last 24h)
    recent_users = users_collection.find({
        "last_seen": {"$gt": datetime.now(timezone.utc) - timedelta(hours=24)}
    })

    for user in recent_users:
        user_id = user["userId"]
        old_score = user.get("suspicion_score", 0.0)
        
        # Get their recent queries
        recent_queries = list(query_logs_collection.find({
            "userId": user_id,
            "timestamp": {"$gt": datetime.now(timezone.utc) - timedelta(minutes=5)}
        }))
        
        if not recent_queries:
            # No recent activity, decay the score
            new_score = old_score * 0.9 # 10% decay
        else:
            v_score = calculate_v_score(recent_queries)
            d_score = calculate_d_score(recent_queries)
            
            # Weighted average for the real-time score
            # 60% velocity, 40% similarity
            real_time_score = (0.6 * v_score) + (0.4 * d_score)
            
            # New score is the higher of the decayed old score or the new real-time score
            decayed_score = old_score * 0.9
            new_score = max(decayed_score, real_time_score)
        
        new_score = round(new_score, 4)

        # Update the user's score in the database
        users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"suspicion_score": new_score, "last_seen": datetime.now(timezone.utc)}}
        )

        print(f"  - User: {user_id} | Old Score: {old_score:.4f} | New Score: {new_score:.4f}")

        # --- TIER 3 ESCALATION & AUDIT ---
        if new_score >= 0.95 and old_score < 0.95:
            print(f"  🚨 TIER 3 ESCALATION: User {user_id} crossed threshold!")
            try:
                # Log to Blockchain and get back tx_hash and threat_id
                log_result = log_threat_to_blockchain(
                    db=db,
                    user_id=user_id,
                    attack_type="High Velocity & Similarity"
                )
                print(f"  ✅ Logged to Blockchain! Tx: {log_result['tx_hash']}")
            except Exception as e:
                print(f"  ❌ FAILED to log to blockchain: {e}")
                
    print(f"[Analysis Job] Completed.")
