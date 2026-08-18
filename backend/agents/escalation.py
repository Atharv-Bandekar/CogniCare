import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def evaluate_escalation_need(recent_insights: List[Dict[str, Any]]) -> bool:
    """
    Evaluates recent interaction insights to determine if a caregiver needs to be alerted.
    
    Args:
        recent_insights (List[Dict[str, Any]]): A list of recent insight dictionaries, 
                                                ordered chronologically (oldest to newest).
        
    Returns:
        bool: True if an alert should be triggered, False otherwise.
    """
    if not recent_insights:
        return False

    # WHY: We check for safety flags first. Even if engagement is high, confusion 
    # or distress in a single interaction warrants an immediate, gentle caregiver nudge.
    for insight in recent_insights:
        if insight.get("safety_flag") is True:
            logger.info("Escalation triggered: Safety flag detected in recent insights.")
            return True

    # WHY: We look for a pattern of 3 consecutive 'low' engagements to detect isolation or withdrawal.
    # We slice `[-3:]` to ensure we are only evaluating the absolute most recent sequence.
    last_three = recent_insights[-3:]
    
    if len(last_three) == 3 and all(i.get("engagement_level") == "low" for i in last_three):
        logger.info("Escalation triggered: 3 consecutive low engagement interactions.")
        return True

    return False