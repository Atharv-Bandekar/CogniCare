"""
Configuration file for Dynamic Difficulty Adjustment (DDA) thresholds.
WHY: Extracting these into a config file allows non-engineers or parallel developers 
to tune the engagement logic without touching the core agent orchestration code.
"""

# Threshold below which a user is considered to have low engagement, triggering easier questions.
LOW_ENGAGEMENT_THRESHOLD = 0.4

# Threshold above which a user is highly engaged, triggering open-ended, complex questions.
HIGH_ENGAGEMENT_THRESHOLD = 0.7

# The number of recent interaction scores to average when calculating current difficulty.
ENGAGEMENT_LOOKBACK_DAYS = 3