from .base import call_llm

class CoordinatorAgent:
    FALLBACK_ACTIVITIES = {
        "Positive": "You sound in great spirits! Try calling a family member to share that memory with them today.",
        "Neutral": "Take 15 minutes to look through an old photo album — it's a lovely way to relax this afternoon.",
        "Negative": "It might help to sit somewhere sunny with a warm drink for 10 minutes and listen to a favorite old song.",
    }

    def generate_activity(self, user_text, evaluation):
        system_prompt = (
            "You are an empathetic, insightful cognitive-wellness companion. The user has just "
            "shared a memory. Validate their specific memory warmly in one short sentence. Then, "
            "suggest one highly specific, gentle offline activity related to the emotion or subject "
            "of their memory. Avoid generic advice like 'take a walk' or 'call a friend' unless it "
            "directly ties to their story. Keep the tone conversational, human, and deeply personalized. "
            "Under 40 words total."
        )
        user_prompt = (
            f"User's answer: \"{user_text}\"\n"
            f"Detected sentiment: {evaluation['sentiment_label']} (score {evaluation['sentiment_score']})\n"
            f"Detected engagement level: {evaluation['engagement_level']}\n\n"
            "Suggest today's offline activity."
        )

        result = call_llm(system_prompt, user_prompt, max_tokens=100)
        
        if result:
            return result.strip().strip('"').strip()

        return self.FALLBACK_ACTIVITIES.get(
            evaluation["sentiment_label"], self.FALLBACK_ACTIVITIES["Neutral"]
        )