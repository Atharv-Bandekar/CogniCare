import threading
import customtkinter as ctk
from tkinter import ttk, messagebox
from src.agents.base import translate_to_english, translate_text
from src.database.db import (
    get_demo_user_id,
    log_conversation,
    log_insight,
    fetch_history
)
from src.agents.interviewer import InterviewerAgent
from src.agents.evaluator import EvaluatorAgent
from src.agents.coordinator import CoordinatorAgent
from src.utils.audio import play_audio, record_audio

# System Appearance & Color Theme
ctk.set_appearance_mode("System")  # Follows OS theme (Dark/Light)
ctk.set_default_color_theme("blue")


class CogniCareApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("CogniCare AI - Cognitive Engagement Assistant")
        self.geometry("950x850")
        self.minsize(900, 750)

        # Agents & State Initialization
        self.interviewer = InterviewerAgent()
        self.evaluator = EvaluatorAgent()
        self.coordinator = CoordinatorAgent()

        self.user_id = get_demo_user_id()
        self.original_question = None
        self.current_question = None
        self.current_conversation_id = None

        self.voice_mode = ctk.BooleanVar(value=False)
        self.selected_lang = ctk.StringVar(value="English")

        self._build_ui()

        # Load DeBERTa asynchronously
        threading.Thread(target=self.evaluator.load_model, daemon=True).start()
        
        # Kick off Agent 1
        self.after(200, self.run_agent_1)

    def _build_ui(self):
        # Master Tabview for Navigation
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.checkin_tab = self.tabview.add("  Daily Check-In  ")
        self.dashboard_tab = self.tabview.add("  Caregiver Dashboard  ")

        self._build_checkin_tab()
        self._build_dashboard_tab()

    # -------------------------------------------------- DAILY CHECK-IN TAB --
    def _build_checkin_tab(self):
        tab = self.checkin_tab

        # Top Bar Controls (Language + Voice Switch)
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(5, 10))

        lang_label = ctk.CTkLabel(top_bar, text="Language:", font=ctk.CTkFont(size=14, weight="bold"))
        lang_label.pack(side="left", padx=(0, 10))

        self.lang_dropdown = ctk.CTkOptionMenu(
            top_bar,
            values=["English", "Hindi", "Marathi", "Tamil"],
            variable=self.selected_lang,
            command=self.on_language_change,
            width=120
        )
        self.lang_dropdown.pack(side="left")

        self.voice_switch = ctk.CTkSwitch(
            top_bar,
            text="🎤 Voice Mode",
            variable=self.voice_mode,
            command=self.toggle_voice_mode,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.voice_switch.pack(side="right")

        # Header Title & Dynamic Status
        title_label = ctk.CTkLabel(
            tab, 
            text="CogniCare AI", 
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(10, 2))

        self.status_label = ctk.CTkLabel(
            tab, 
            text="Preparing today's question...", 
            font=ctk.CTkFont(size=14), 
            text_color="gray"
        )
        self.status_label.pack(pady=(0, 15))

        # Question Display Card
        self.q_card = ctk.CTkFrame(tab, corner_radius=12)
        self.q_card.pack(fill="x", padx=15, pady=5)

        self.question_label = ctk.CTkLabel(
            self.q_card,
            text="",
            font=ctk.CTkFont(family="Arial", size=22, weight="bold"), 
            wraplength=800,
            justify="center"
        )
        self.question_label.pack(padx=20, pady=20)

        # "Try Another Question" Action
        self.refresh_q_btn = ctk.CTkButton(
            tab,
            text="🔄 Try Another Question",
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            command=self.run_agent_1,
            width=180
        )
        self.refresh_q_btn.pack(pady=(5, 15))

        # Input Section Container
        self.input_card = ctk.CTkFrame(tab, fg_color="transparent")
        self.input_card.pack(fill="x", padx=15, pady=5)

        self.response_text = ctk.CTkTextbox(
            self.input_card,
            height=110,
            font=ctk.CTkFont(size=14),
            corner_radius=10
        )
        self.response_text.pack(fill="x", expand=True, padx=10, pady=10)

        self.mic_btn = ctk.CTkButton(
            self.input_card,
            text="🔴 Tap to Record Answer",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#D9534F",
            hover_color="#C9302C",
            height=45,
            command=self.record_voice_answer
        )

        # Submit Button
        self.submit_btn = ctk.CTkButton(
            tab,
            text="Submit My Answer",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            command=self.run_agent_2_and_3
        )
        self.submit_btn.pack(pady=15)

        # Recommendation Card (Initially Hidden)
        self.activity_card = ctk.CTkFrame(tab, corner_radius=12, border_width=1, border_color=("#2E6F95", "#4A90E2"))
        
        # Swapped CTkLabel for a scrolling CTkTextbox
        self.activity_text = ctk.CTkTextbox(
            self.activity_card,
            font=ctk.CTkFont(size=15),
            height=200,          # Gives it a nice tall height
            wrap="word",         # Wraps text at the edge of the box
            fg_color="transparent" # Blends in with the background
        )
        self.activity_text.pack(fill="both", expand=True, padx=15, pady=15)

    # ----------------------------------------------- CAREGIVER DASHBOARD TAB --
    def _build_dashboard_tab(self):
        tab = self.dashboard_tab

        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            header, text="Caregiver Dashboard", font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Refresh", width=100, command=self.refresh_dashboard
        ).pack(side="right")

        # Treeview Container
        tree_frame = ctk.CTkFrame(tab, corner_radius=10)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        columns = ("timestamp", "question", "response", "sentiment", "engagement", "activity")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        headings = {
            "timestamp": "Date/Time", "question": "Question",
            "response": "Response", "sentiment": "Sentiment",
            "engagement": "Engagement", "activity": "Recommended Activity",
        }
        widths = {
            "timestamp": 120, "question": 160, "response": 180,
            "sentiment": 90, "engagement": 90, "activity": 220,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        vsb.pack(side="right", fill="y", pady=10)

    # ----------------------------------------------------- EVENT HANDLERS --
    def toggle_voice_mode(self):
        if self.voice_mode.get():
            self.response_text.pack_forget()
            self.mic_btn.pack(fill="x", expand=True)
            if self.current_question:
                play_audio(self.current_question, self.selected_lang.get())
        else:
            self.mic_btn.pack_forget()
            self.response_text.pack(fill="x", expand=True)

    def record_voice_answer(self):
        self.status_label.configure(text="Listening... Please speak now.")
        self.mic_btn.configure(state="disabled", text="Recording...")

        def worker():
            text = record_audio(self.selected_lang.get())
            self.after(0, self._on_record_done, text)

        threading.Thread(target=worker, daemon=True).start()

    def _on_record_done(self, text):
        self.mic_btn.configure(state="normal", text="🔴 Tap to Record Answer")
        if text:
            self.response_text.delete("1.0", "end")
            self.response_text.insert("1.0", text)
            self.status_label.configure(text="Audio captured! Review or click submit when ready.")
            if self.voice_mode.get():
                self.response_text.pack(fill="x", expand=True, pady=(10, 0))
        else:
            self.status_label.configure(text="Could not hear you clearly. Please try again.")

    def refresh_dashboard(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for rec in fetch_history():
            self.tree.insert("", "end", values=(
                rec["timestamp"][:19].replace("T", " "),
                rec["question"],
                (rec["response"] or "")[:60],
                rec["sentiment_label"] or "-",
                rec["engagement_level"] or "-",
                rec["recommended_activity"] or "-",
            ))

    def on_language_change(self, choice):
        """Translates the current question instead of generating a new one."""
        if not self.original_question:
            self.run_agent_1()
            return

        self.status_label.configure(text=f"Translating to {choice}...")
        self.submit_btn.configure(state="disabled")
        self.refresh_q_btn.configure(state="disabled")

        def worker():
            # ALWAYS translate from the pristine anchor text
            translated_q = translate_text(self.original_question, choice)
            self.after(0, self._on_translation_done, translated_q, choice)

        threading.Thread(target=worker, daemon=True).start()

    def _on_translation_done(self, translated_q, target_lang):
        self.current_question = translated_q
        self.question_label.configure(text=f"\n{translated_q}\n")
        self.status_label.configure(text="Please answer below:")
        
        self.submit_btn.configure(state="normal")
        self.refresh_q_btn.configure(state="normal")

        # If voice mode is on, read the newly translated question aloud
        if self.voice_mode.get():
            self.response_text.pack_forget()
            play_audio(translated_q, target_lang)

    def run_agent_1(self):
        self.status_label.configure(text="Thinking of a question for you...")
        self.question_label.configure(text="")
        self.submit_btn.configure(state="disabled")
        self.refresh_q_btn.configure(state="disabled")

        def worker():
            # 1. Fetch the history from SQLite
            history = fetch_history()
            
            # 2. Extract just the question strings into a list
            past_questions = [rec["question"] for rec in history] if history else []
            
            # 3. Pass that list to the agent
            question = self.interviewer.generate_question(
                language=self.selected_lang.get(), 
                past_questions=past_questions
            )
            
            self.after(0, self._on_agent_1_done, question)
            
        threading.Thread(target=worker, daemon=True).start()

    def _on_agent_1_done(self, question):
        self.original_question = question
        self.current_question = question
        self.question_label.configure(text=f"\n{question}\n")
        self.status_label.configure(text="Please answer below:")

        self.submit_btn.configure(state="normal", text="Submit My Answer")
        self.refresh_q_btn.configure(state="normal")
        self.response_text.configure(state="normal")
        self.response_text.delete("1.0", "end")
        self.activity_card.pack_forget()

        if self.voice_mode.get():
            self.response_text.pack_forget()
            play_audio(question, self.selected_lang.get())

    def run_agent_2_and_3(self):
        user_text = self.response_text.get("1.0", "end").strip()
        if not user_text:
            messagebox.showinfo("CogniCare AI", "Please provide an answer first.")
            return

        self.submit_btn.configure(state="disabled")
        self.refresh_q_btn.configure(state="disabled")
        self.status_label.configure(text="Analyzing your response...")
        self.activity_card.pack_forget()

        self.current_conversation_id = log_conversation(
            self.user_id, self.current_question, user_text
        )

        def worker():
            eval_text = translate_to_english(user_text, self.selected_lang.get())
            evaluation = self.evaluator.analyze(eval_text)

            self.after(0, self.status_label.configure, {"text": "Preparing a personalized activity..."})

            # Pass the selected language to Agent 3
            activity = self.coordinator.generate_activity(
                user_text, 
                evaluation, 
                language=self.selected_lang.get()
            )

            log_insight(
                self.current_conversation_id,
                evaluation["sentiment_label"], evaluation["sentiment_score"],
                evaluation["engagement_level"], evaluation["engagement_score"],
                activity,
            )

            self.after(0, self._on_pipeline_done, evaluation, activity)

        threading.Thread(target=worker, daemon=True).start()

    def _on_pipeline_done(self, evaluation, activity):
        self.status_label.configure(
            text=f"Detected mood: {evaluation['sentiment_label']}  |  "
                 f"Engagement: {evaluation['engagement_level']}"
        )
        
        # 1. Format the JSON into readable text
        if isinstance(activity, dict):
            display_text = (
                f"🌅 Morning: {activity.get('morning_activity', '')}\n\n"
                f"☀️ Afternoon: {activity.get('afternoon_activity', '')}\n\n"
                f"🌙 Evening: {activity.get('evening_activity', '')}\n\n"
                f"💡 Caregiver Note: {activity.get('caregiver_rationale', '')}"
            )
            # Create a natural-sounding script for the Voice Mode (excluding the rationale)
            audio_text = (
                f"Here is a wonderful plan for you today. "
                f"For the morning: {activity.get('morning_activity', '')}. "
                f"In the afternoon: {activity.get('afternoon_activity', '')}. "
                f"And for the evening: {activity.get('evening_activity', '')}."
            )
        else:
            # Fallback just in case the LLM returned a raw string
            display_text = str(activity)
            audio_text = str(activity)

        # 2.  UI
        self.activity_card.pack(fill="x", padx=15, pady=15)
        
        #  
        self.activity_text.configure(state="normal")
        self.activity_text.delete("1.0", "end")
        self.activity_text.insert("1.0", f"Today's suggested activity plan:\n\n{display_text}")
        self.activity_text.configure(state="disabled")

        self.response_text.configure(state="disabled")
        self.submit_btn.configure(state="disabled", text="Check-In Completed")

        self.refresh_dashboard()

        # 3. natural audio script 
        if self.voice_mode.get():
            play_audio(audio_text, self.selected_lang.get())