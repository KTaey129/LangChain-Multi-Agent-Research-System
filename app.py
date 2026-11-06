import logging
import os
import re
from dataclasses import dataclass

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

REQUIRED_KEYS = ("OPENAI_API_KEY", "TAVILY_API_KEY")
MAX_TOPIC_LENGTH = 200
MAX_FILENAME_LENGTH = 50
EXAMPLE_TOPICS = (
    "The impact of AI on the job market in 2026",
    "Current state of solid-state battery technology",
    "How remote work is reshaping commercial real estate",
)
# pipeline step -> (display label, key in the pipeline's returned state)
STEPS = {
    "search": ("Search agent", "search_result"),
    "read": ("Reader agent", "scraped_content"),
    "write": ("Writer", "report"),
    "critique": ("Critic", "feedback"),
}


@dataclass(frozen=True)
class CriticFeedback:
    score: float | None
    strengths: str | None
    improvements: str | None
    verdict: str | None


def _section(text: str, label: str, next_label: str | None) -> str | None:
    end = rf"(?=\n\s*{next_label}:|\Z)" if next_label else r"\Z"
    match = re.search(rf"{label}:\s*(.*?){end}", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_critic_feedback(text: str) -> CriticFeedback:
    score_match = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", text, re.IGNORECASE)
    return CriticFeedback(
        score=float(score_match.group(1)) if score_match else None,
        strengths=_section(text, "Strengths", "Areas to improve"),
        improvements=_section(text, "Areas to improve", "One line verdict"),
        verdict=_section(text, "One line verdict", None),
    )


def escape_dollars(text: str) -> str:
    # st.markdown treats paired "$" as LaTeX, which mangles dollar amounts
    return text.replace("$", r"\$")


def report_filename(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:MAX_FILENAME_LENGTH]
    return f"{slug or 'report'}.md"


def missing_api_keys() -> list[str]:
    return [key for key in REQUIRED_KEYS if not os.getenv(key)]


def set_topic(topic: str) -> None:
    st.session_state.topic = topic


def clear_results() -> None:
    st.session_state.update({"result": None, "error": None, "result_topic": ""})


def run_research(topic: str) -> None:
    clear_results()
    collected: dict[str, str | None] = {}

    with st.status("Running research pipeline...", expanded=True) as status:
        slots = {step: st.empty() for step in STEPS}
        for step, (label, _) in STEPS.items():
            slots[step].markdown(f"⚪ {label} — waiting")

        def on_step(step: str, step_status: str, output: str | None) -> None:
            label, state_key = STEPS[step]
            if step_status == "running":
                slots[step].markdown(f"⏳ **{label}** — working...")
                return
            collected[state_key] = output
            slots[step].markdown(f"✅ **{label}** — done")

        try:
            # imported lazily: agents/tools read API keys at import time
            from src.pipeline.pipeline import research_pipeline

            result = research_pipeline(topic, on_step=on_step)
        except Exception as exc:
            logger.exception("Research pipeline failed")
            status.update(label="Pipeline failed", state="error")
            st.session_state.update({
                "result": dict(collected),
                "error": (
                    f"The pipeline stopped early ({type(exc).__name__}). "
                    "Check the terminal logs for details."
                ),
                "result_topic": topic,
            })
            return

        status.update(label="Research complete", state="complete", expanded=False)

    st.session_state.update({"result": result, "error": None, "result_topic": topic})


def render_critic(feedback: str) -> None:
    parsed = parse_critic_feedback(feedback)
    if parsed.score is None:
        st.markdown(escape_dollars(feedback))
        return

    st.metric("Score", f"{parsed.score:g}/10")
    strengths_col, improve_col = st.columns(2)
    with strengths_col:
        st.subheader("Strengths")
        st.markdown(escape_dollars(parsed.strengths or "—"))
    with improve_col:
        st.subheader("Areas to improve")
        st.markdown(escape_dollars(parsed.improvements or "—"))
    if parsed.verdict:
        st.info(escape_dollars(parsed.verdict))


def render_results(result: dict, topic: str) -> None:
    report_tab, critic_tab, sources_tab = st.tabs(["Report", "Critic", "Sources"])

    with report_tab:
        report = result.get("report")
        if report:
            st.markdown(escape_dollars(report))
            st.download_button(
                "Download report (.md)",
                data=report,
                file_name=report_filename(topic),
                mime="text/markdown",
            )
        else:
            st.info("No report was produced.")

    with critic_tab:
        feedback = result.get("feedback")
        if feedback:
            render_critic(feedback)
        else:
            st.info("No critic feedback was produced.")

    with sources_tab:
        search_result = result.get("search_result")
        scraped_content = result.get("scraped_content")
        with st.expander("Search results", expanded=bool(search_result)):
            st.markdown(escape_dollars(search_result or "Not available."))
        with st.expander("Scraped content"):
            st.text(scraped_content or "Not available.")


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Multi-Agent Research")
        st.write(
            "Four agents work in sequence: search the web, scrape the best "
            "source, write a report, then critique it."
        )
        st.subheader("Example topics")
        for example in EXAMPLE_TOPICS:
            st.button(example, on_click=set_topic, args=(example,), use_container_width=True)
        st.divider()
        st.button("Clear results", on_click=clear_results, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Multi-Agent Research", page_icon="🔎", layout="wide")
    st.session_state.setdefault("topic", "")
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("error", None)
    st.session_state.setdefault("result_topic", "")

    render_sidebar()

    st.title("🔎 Multi-Agent Research System")
    st.caption("Each run makes several paid OpenAI and Tavily API calls.")

    missing = missing_api_keys()
    if missing:
        st.error(f"Missing environment variables: {', '.join(missing)}. Add them to your .env file.")

    topic = st.text_input(
        "Research topic",
        key="topic",
        max_chars=MAX_TOPIC_LENGTH,
        placeholder="e.g. The impact of AI on the job market in 2026",
    ).strip()

    if st.button("Run research", type="primary", disabled=bool(missing) or not topic):
        run_research(topic)

    if st.session_state.error:
        st.error(st.session_state.error)
    if st.session_state.result:
        render_results(st.session_state.result, st.session_state.result_topic)


main()
