"""The AI reader: sends one report, gets back the fixed fields, or a reason there is no usable answer.

Fail-safe means UP: every way this can go wrong becomes a Failure, and a Failure goes to the top of the queue.
Report text is never written to a log, a file or an error message here.
"""
import os
from dataclasses import dataclass

import anthropic
from pydantic import ValidationError

import config
from triage.loader import Report
from triage.models import Failure, IncidentReading, Outcome
from triage.prompt import build_system_prompt, build_user_message
from triage.reference import Reference

MAX_OUTPUT_TOKENS = 2000
DEFAULT_TIMEOUT_SECONDS = 60.0


class MissingKey(Exception):
    """No API key is set. The message never contains a key."""


@dataclass(frozen=True)
class ReadResult:
    outcome: Outcome
    model_used: str | None = None        # what the service says it used (checked against the one asked for)
    input_tokens: int = 0
    output_tokens: int = 0


def make_client(timeout: float = DEFAULT_TIMEOUT_SECONDS) -> anthropic.Anthropic:
    """The key comes from the environment (or Streamlit secrets copied into it). It is never read from a file in the repo."""
    config.load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise MissingKey("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(timeout=timeout, max_retries=0)    # retries are done by the runner, with jitter


def read_report(client, report: Report, ref: Reference, model: str | None = None,
                timeout: float = DEFAULT_TIMEOUT_SECONDS) -> ReadResult:
    """One report in, one ReadResult out. Never raises for a bad answer or a service problem."""
    model = model or config.MODEL
    try:
        response = client.messages.parse(
            model=model, max_tokens=MAX_OUTPUT_TOKENS, timeout=timeout,
            system=build_system_prompt(ref),
            messages=[{"role": "user", "content": build_user_message(report)}],
            output_format=IncidentReading,
        )
    except anthropic.APITimeoutError:
        return ReadResult(Failure.timed_out)
    except anthropic.APIError:
        return ReadResult(Failure.service_error)
    except ValidationError:
        return ReadResult(Failure.invalid_answer)
    except Exception:                      # anything unexpected still fails UP, with no detail kept
        return ReadResult(Failure.service_error)

    usage = getattr(response, "usage", None)
    tokens = dict(input_tokens=getattr(usage, "input_tokens", 0) or 0, output_tokens=getattr(usage, "output_tokens", 0) or 0)
    used = getattr(response, "model", None)
    if getattr(response, "stop_reason", None) == "refusal":
        return ReadResult(Failure.refused, used, **tokens)
    reading = getattr(response, "parsed_output", None)
    if not isinstance(reading, IncidentReading):
        return ReadResult(Failure.invalid_answer, used, **tokens)
    if reading.report_id != report.report_id:
        return ReadResult(Failure.wrong_report, used, **tokens)
    return ReadResult(reading, used, **tokens)
