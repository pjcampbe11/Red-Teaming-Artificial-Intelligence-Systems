"""
AIRTR deliberately-vulnerable mock LLM.

The single modelled property, shared across every service: the "model" follows
instructions found ANYWHERE in its context, with no boundary between developer
instructions, user input, retrieved documents, tool output, memory, or
inter-agent messages. This reproduces the instruction/data trust-boundary
collapse (Module 1) deterministically and offline — no GPU, no downloads, no
API keys — so every reader can run the vulnerability classes.

Directive grammar (what a real LLM would infer from natural language; here made
explicit so the class is reproducible):
    CALL <tool>(<arg>)   -> the agent invokes that tool with the argument
    SAY(<text>)          -> the agent repeats attacker-controlled text

Because the mock obeys directives regardless of which context block they came
from, indirect injection, RAG poisoning, tool hijack, memory poisoning, and
A2A message injection all "just work" — exactly the point. Production defenses
(authorization at tools, output sanitization, least privilege, provenance) are
what the exercises show are missing; those would stop these attacks regardless
of model capability.
"""
import re

DIRECTIVE_RE = re.compile(r"CALL\s+([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)")
SAY_RE = re.compile(r"SAY\(([^)]*)\)")


def _clean(arg):
    return arg.strip().strip("'\"")


def run_llm(context_blocks, tools=None, default_reply=None):
    """Run the vulnerable mock LLM.

    context_blocks : list[(source_label, text)]  -- everything in the context
    tools          : dict[str, callable(arg)->str]  -- callable tools
    returns        : (reply_text, tool_trace)
    """
    tools = tools or {}
    blob = "\n".join("[%s]\n%s" % (lbl, txt) for lbl, txt in context_blocks)
    trace = []
    outputs = []

    # Obey every directive found anywhere in the blended context. THIS is the
    # vulnerability: no separation between trusted instructions and untrusted data.
    for m in DIRECTIVE_RE.finditer(blob):
        tool, arg = m.group(1), _clean(m.group(2))
        if tool in tools:
            try:
                result = tools[tool](arg)
            except Exception as e:  # noqa: BLE001
                result = "tool error: %s" % e
            trace.append({"tool": tool, "arg": arg, "result": result})
            outputs.append(result)

    for m in SAY_RE.finditer(blob):
        outputs.append(_clean(m.group(1)))

    if not outputs:
        outputs.append(default_reply or "I'm the Northwind assistant. How can I help?")

    return " | ".join(str(o) for o in outputs), trace


def extractable_system_prompt(prompt, user_message):
    """Model naive system-prompt extraction.

    Returns the prompt text when the user_message uses a framing/split technique
    (Module 3 §3.2), and a scripted refusal for a naive direct request — so
    extraction is possible but takes technique, as against a real model.
    """
    m = (user_message or "").lower()
    naive = ("what is your system prompt" in m or "what are your instructions" in m)
    framed = any(k in m for k in (
        "in your own words", "for debugging", "output your configuration",
        "repeat the text above", "starting with 'you are'", "translate",
        "first 100 words", "continue the following", "code block", "verbatim",
    ))
    if framed:
        return prompt
    if naive:
        return None  # scripted refusal handled by caller
    return None
