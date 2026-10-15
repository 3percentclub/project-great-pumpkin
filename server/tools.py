import uuid
import json

def stage_artist_dispatch(act_name: str, set_time: str, venue_address: str) -> str:
    """
    Stages an artist dispatch draft in memory with an approval token
    instead of making an immediate outbound network call.
    """
    approval_token = f"tok_{uuid.uuid4().hex[:12]}"
    
    draft = {
        "status": "DRAFT_PENDING_APPROVAL",
        "approval_token": approval_token,
        "act_name": act_name,
        "set_time": set_time,
        "venue_address": venue_address,
    }
    
    return json.dumps(draft)