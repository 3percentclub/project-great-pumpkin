import json
import sys
from pathlib import Path

# Add project root to sys.path so we can import server.tools
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.tools import stage_artist_dispatch

def test_gated_tool_prevents_auto_send():
    act_name = "The Great Pumpkin Band"
    set_time = "2026-10-31 20:00"
    venue_address = "123 Patch Lane, Brooklyn, NY"
    
    # Call the gated tool
    result_str = stage_artist_dispatch(act_name, set_time, venue_address)
    
    # Ensure it returns valid JSON string
    data = json.loads(result_str)
    
    # Verify the safety protocol requirements
    assert data["status"] == "DRAFT_PENDING_APPROVAL"
    assert "approval_token" in data
    assert data["approval_token"].startswith("tok_")
    assert data["act_name"] == act_name
    assert data["set_time"] == set_time
    assert data["venue_address"] == venue_address