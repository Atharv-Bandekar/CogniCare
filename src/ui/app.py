import threading
import tkinter as tk
from tkinter import ttk, messagebox

from src.database.db import (
    get_demo_user_id,
    log_conversation,
    log_insight,
    fetch_history
)
from src.agents.interviewer import InterviewerAgent
from src.agents.evaluator import EvaluatorAgent
from src.agents.coordinator import CoordinatorAgent

BG_COLOR = "#F5F7FA"
ACCENT_COLOR = "#2E6F95"
FONT_LARGE = ("Helvetica", 20, "bold")
FONT_MED = ("Helvetica", 14)
FONT_BTN = ("Helvetica", 16, "bold")


class CogniCareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CogniCare AI - Cognitive Engagement Assistant")
        self.root.geometry("900x700")
        self.root.configure(bg=BG_COLOR)

        # Initialize Agents
        self.interviewer = InterviewerAgent()
        self.evaluator = EvaluatorAgent()
        self.coordinator = CoordinatorAgent()

        # State
        self.user_id = get_demo_user_id()
        self.current_question = None
        self.current_conversation_id = None

        self._build_notebook()

        # Background thread to load DeBERTa
        threading.Thread(target=self.evaluator.load_model, daemon=True).start()

        # Kickoff Agent 1
        self.root.after(200, self.run_agent_1)

    def _build_notebook(self):
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=FONT_MED, padding=[16, 8])

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.checkin_tab = tk.Frame(notebook, bg=BG_COLOR)
        self.dashboard_tab = tk.Frame(notebook, bg=BG_COLOR)

        notebook.add(self.checkin_tab, text="  Daily Check-In  ")
        notebook.add(self.dashboard_tab, text="  Caregiver Dashboard  ")

        self._build_checkin_tab()
        self._build_dashboard_tab()

        notebook.bind("<<NotebookTabChanged>>", lambda e: self.refresh_dashboard())

    def _build_checkin_tab(self):
        frame = self.checkin_tab

        tk.Label(frame, text="CogniCare AI", font=("Helvetica", 26, "bold"),
                 bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=(20, 5))

        self.status_label = tk.Label(frame, text="Preparing today's question...",
                                     font=FONT_MED, bg=BG_COLOR, fg="#666666")
        self.status_label.pack(pady=(0, 10))

        self.question_label = tk.Label(
            frame, text="", font=FONT_LARGE, bg=BG_COLOR, fg="#222222",
            wraplength=800, justify="center"
        )
        self.question_label.pack(pady=15, padx=20)

        self.response_text = tk.Text(frame, height=5, width=60, font=FONT_MED,
                                     wrap="word", relief="solid", borderwidth=1)
        self.response_text.pack(pady=10, padx=20)

        self.submit_btn = tk.Button(
            frame, text="Submit My Answer", font=FONT_BTN, bg=ACCENT_COLOR,
            fg="white", activebackground="#245a7a", relief="flat",
            padx=20, pady=10, command=self.run_agent_2_and_3
        )
        self.submit_btn.pack(pady=10)

        self.activity_frame = tk.Frame(frame, bg="#E8F0F5", relief="groove", borderwidth=1)
        self.activity_label = tk.Label(
            self.activity_frame, text="", font=FONT_MED, bg="#E8F0F5",
            fg="#1E4E6B", wraplength=780, justify="left"
        )
        self.activity_label.pack(padx=20, pady=15)

    def _build_dashboard_tab(self):
        frame = self.dashboard_tab

        header = tk.Frame(frame, bg=BG_COLOR)
        header.pack(fill="x", pady=10, padx=10)
        tk.Label(header, text="Caregiver Dashboard", font=("Helvetica", 18, "bold"),
                 bg=BG_COLOR, fg=ACCENT_COLOR).pack(side="left")
        tk.Button(header, text="Refresh", font=("Helvetica", 11), command=self.refresh_dashboard
                  ).pack(side="right")

        columns = ("timestamp", "question", "response", "sentiment", "engagement", "activity")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=18)
        
        headings = {
            "timestamp": "Date/Time", "question": "Question",
            "response": "Response", "sentiment": "Sentiment",
            "engagement": "Engagement", "activity": "Recommended Activity",
        }
        widths = {
            "timestamp": 130, "question": 160, "response": 180,
            "sentiment": 90, "engagement": 90, "activity": 220,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", pady=10)

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

    def run_agent_1(self):
        self.status_label.config(text="Thinking of a question for you...")
        self.question_label.config(text="")
        self.submit_btn.config(state="disabled")

        def worker():
            question = self.interviewer.generate_question()
            self.root.after(0, self._on_agent_1_done, question)

        threading.Thread(target=worker, daemon=True).start()

    def _on_agent_1_done(self, question):
        self.current_question = question
        self.question_label.config(text=question)
        self.status_label.config(text="Please type your answer below:")
        self.submit_btn.config(state="normal", text="Submit My Answer")
        self.response_text.config(state="normal")
        self.activity_frame.pack_forget()

    def run_agent_2_and_3(self):
        user_text = self.response_text.get("1.0", "end").strip()
        if not user_text:
            messagebox.showinfo("CogniCare AI", "Please type an answer first.")
            return

        self.submit_btn.config(state="disabled")
        self.status_label.config(text="Analyzing your response...")
        self.activity_frame.pack_forget()

        self.current_conversation_id = log_conversation(
            self.user_id, self.current_question, user_text
        )

        def worker():
            evaluation = self.evaluator.analyze(user_text)
            self.root.after(0, self.status_label.config,
                             {"text": "Preparing a personalized activity..."})

            activity = self.coordinator.generate_activity(user_text, evaluation)

            log_insight(
                self.current_conversation_id,
                evaluation["sentiment_label"], evaluation["sentiment_score"],
                evaluation["engagement_level"], evaluation["engagement_score"],
                activity,
            )

            self.root.after(0, self._on_pipeline_done, evaluation, activity)

        threading.Thread(target=worker, daemon=True).start()

    def _on_pipeline_done(self, evaluation, activity):
        self.status_label.config(
            text=f"Detected mood: {evaluation['sentiment_label']}  |  "
                 f"Engagement: {evaluation['engagement_level']}"
        )
        self.activity_label.config(text=f"Today's suggested activity:\n\n{activity}")
        self.activity_frame.pack(pady=15, padx=20, fill="x")

        # Disable response text box and update button state to end single check-in loop
        self.response_text.config(state="disabled")
        self.submit_btn.config(state="disabled", text="Check-In Completed")
        
        self.refresh_dashboard()