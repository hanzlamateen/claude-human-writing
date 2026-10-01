#!/usr/bin/env python3
"""Flag the habits that make text read as written by Claude or another LLM.

Usage:
  lint_writing.py FILE [FILE...]   check files
  lint_writing.py -                check stdin
  lint_writing.py --json ...       machine-readable report
  lint_writing.py --strict ...     exit 1 on warnings as well as errors

Exit status: 0 clean, 1 errors (or warnings with --strict), 2 bad usage.

Errors are near-certain tells: em dashes, chatbot stock phrases, AI attribution
lines. Warnings are things people also write, but that pile up in AI text:
contrast reframes, stock words, "-ing" tails, uniform sentence lengths. Code
fences, inline code, URLs and short double-quoted spans are skipped, since those
are mentions rather than the writer's own words.

Python 3.8+, standard library only, so it runs the same in a hook, in a shell
and in claude.ai's code sandbox.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from dataclasses import asdict, dataclass, field
from typing import Iterable, List, Optional

# ---------------------------------------------------------------------------
# Rules. Each phrase rule is (rule id, severity, regex, advice).
# ---------------------------------------------------------------------------

DASH_ADVICE = "recast the sentence (two sentences, or reworded) instead of trading the dash for other punctuation"

CHAR_RULES = [
    ("em-dash", "error", re.compile(r"[\u2014\u2015\u2E3A\u2E3B]"), DASH_ADVICE),
    ("spaced-en-dash", "error", re.compile(r"(?<=\S) \u2013 (?=\S)"), DASH_ADVICE),
    ("double-hyphen-dash", "error", re.compile(r"(?<=[A-Za-z,.]) -- (?=[A-Za-z])"), DASH_ADVICE),
]

ATTRIBUTION = [
    r"generated (with|by) (claude|chatgpt|an ai|ai)\b",
    r"co-authored-by:\s*claude",
    r"noreply@anthropic\.com",
    r"\bas an ai( language model)?\b",
    r"\bas a large language model\b",
]

CHATBOT_PHRASES = [
    r"\bi hope (this|that) helps\b",
    r"\bhope (this|that) helps\b",
    r"\byou'?re absolutely right\b",
    r"\bgreat question\b",
    r"\bexcellent question\b",
    r"\bi'?d be (happy|glad) to help\b",
    r"\bhappy to help!",
    r"\blet me know if you have any (other |further |more )?questions\b",
    r"(?:^|(?<=[\n.!?]\s))(?:certainly|absolutely|of course)!",
]

STRONG_STOCK = [
    r"\bdelv(e|es|ed|ing)\b",
    r"\btapestr(y|ies)\b",
    r"\b(is|stands as|serves as) a testament\b",
    r"\ba testament to\b",
    r"\bin the (ever-evolving|ever-changing|fast-paced) (world|landscape|realm)\b",
    r"\bin today'?s (fast-paced|digital|ever-changing|modern) (world|age|landscape)\b",
    r"\bever-evolving\b",
    r"\bunlock(ing)? the (full )?(power|potential)\b",
    r"\bnavigat(e|ing) the (complexities|intricacies|nuances)\b",
]

CONTRAST_REFRAMES = [
    # "not just X, but Y" / "not only X but also Y"
    r"\bnot (just|only|merely|simply) [^.;!?\n]{1,80}?,? but( also| rather)?\b",
    # "It's not X, it's Y" in one sentence
    r"\b(it'?s|it is|this is|that'?s|that is|they'?re|they are)\s+not\s+[^.;!?\n]{1,60}?[,;:]\s*(it'?s|it is|this is|that'?s|that is|they'?re|they are)\b",
    # "This isn't about X. It's about Y." across two sentences
    r"\b(isn'?t|is not|aren'?t|are not|wasn'?t|was not)\s+(just\s+|only\s+|really\s+)?about\s+[^.;!?\n]{1,60}?[.;]\s+(it'?s|it is|it was|they'?re|this is)\s+about\b",
    r"\b(isn'?t|is not|aren'?t|are not)\s+(just\s+|only\s+|merely\s+)[^.;!?\n]{1,50}?[.;]\s+(it'?s|it is|they'?re|they are|this is)\b",
    r"\bless (about|a matter of) [^.;!?\n]{1,60}? (and|than) more (about|a matter of)\b",
    # The split version Claude likes: "This wasn't a bug. It was a missing check."
    r"\b(this|that|it) (wasn'?t|isn'?t|was not|is not) [^.;!?\n]{1,50}[.;] (it|this|that) (was|is|'s)\b",
    r"\bit'?s a real [^.;!?,\n]{1,30}, not\b",
]

SIGNPOSTS = [
    r"\bhere'?s the thing\b",
    r"\bhere'?s (what|how|why) (i|we|you|this|it)\b",
    r"\blet'?s (dive|delve|unpack|break (this|it) down)\b",
    r"\blet'?s take a (closer )?look\b",
    r"\blet me (walk you through|break (this|it) down|unpack)\b",
    r"\b(key|the) takeaways?\b",
    r"\bin (summary|conclusion|a nutshell)\b",
    r"\bto (summarize|summarise|sum up|wrap up)\b",
    r"\bthe bottom line\b",
    r"\bat the end of the day\b",
    r"\ball in all\b",
    r"\bwithout further ado\b",
    r"\bit'?s (worth|important to) (noting|note|mentioning|highlighting|flagging)\b",
    r"\bit is (worth|important to) (noting|note|mentioning|highlighting)\b",
    r"\bworth (noting|flagging|highlighting|calling out)\b",
    r"\bthe (real|key|core|big) (question|issue|problem|insight|story)\b",
    r"\bmake no mistake\b",
    r"\bhonest (caveat|answer|take)\b",
    r"\bsmoking gun\b",
    r"\bthe (one|single) (thing|most important) [^.;!?\n]{0,40}\b(need|correction|change)\b",
    r"\bbuckle up\b",
    r"\bpicture this\b",
]

COLON_REVEAL = re.compile(
    r"(?:^|(?<=\n)|(?<=[.!?] )|(?<=[-*+] )|(?<=\*\*))(?:"
    # Rhetorical setups, with or without "the".
    r"(?:the |here'?s the |one )?(?:kicker|upshot|catch|twist|irony|punchline|bottom line|short version|"
    r"long story short|plot twist|gist|trick|takeaway|verdict|real (?:issue|problem|question|answer|fix|story))"
    # Ordinary nouns turned into a drumroll by "The ...:". Bare labels like "Result: 12 passed" are fine.
    r"|(?:the |here'?s the )(?:fix|result|problem|answer|key|truth|reality|lesson|good news|bad news|net effect|issue|reason|difference|point)"
    r")\s*:",
    re.I,
)

ING_TAIL = re.compile(
    r",\s+(highlighting|underscoring|emphasi[sz]ing|showcasing|reflecting|ensuring|demonstrating|"
    r"illustrating|signal(l)?ing|cementing|solidifying|fostering|paving the way|reinforcing|"
    r"marking a|contributing to|setting the stage|laying the groundwork|making it|allowing (users|you|us|teams|developers)|"
    r"enabling|resulting in|leading to|providing a|giving (users|you|teams))\b",
    re.I,
)

HEDGE_STACK = [
    r"\b(may|might|could) (potentially|possibly|perhaps|conceivably)\b",
    r"\bit (seems|appears) (that )?(it )?(may|might|could)\b",
    r"\bto some extent,? (perhaps|possibly)\b",
]

CHAT_CLOSERS = [
    r"\blet me know if\b",
    r"\bfeel free to\b",
    r"\bhappy to (help|adjust|elaborate|clarify|dig|walk)\b",
    r"\bif you'?d like,? i can\b",
    r"\bwould you like me to\b",
    r"\bdoes (this|that) (help|make sense)\?",
    r"\bgood catch\b",
    r"\bgreat catch\b",
    r"\byou'?re right to\b",
]

# Words that are fine once, but that AI text leans on. Grouped and counted.
STOCK_WORDS = [
    "leverage", "leverages", "leveraged", "leveraging", "utilize", "utilizes", "utilized",
    "utilizing", "utilise", "utilisation", "utilization", "seamless", "seamlessly", "robust",
    "robustness", "crucial", "crucially", "pivotal", "comprehensive", "comprehensively",
    "intricate", "intricacies", "multifaceted", "nuanced", "foster", "fosters", "fostering",
    "underscore", "underscores", "underscored", "underscoring", "showcase", "showcases",
    "showcased", "showcasing", "elevate", "elevates", "elevating", "empower", "empowers",
    "empowering", "harnessing", "streamline", "streamlines", "streamlined",
    "streamlining", "cutting-edge", "game-changer", "game-changing", "paramount", "holistic",
    "synergy", "synergies", "landscape", "realm", "embark", "embarking", "vibrant", "bustling",
    "meticulous", "meticulously", "genuinely", "load-bearing", "notably", "invaluable",
    "unparalleled", "groundbreaking", "transformative", "revolutionize", "revolutionizes",
    "boasts", "nestled", "profound", "profoundly", "resonate", "resonates", "resonating",
    "additionally", "furthermore", "moreover", "noteworthy", "commendable", "insightful",
    "endeavor", "endeavour", "plethora", "myriad", "bolster", "bolsters", "bolstering",
    "garner", "garnered", "enhance", "enhances", "enhancing", "enhancement", "quietly",
    "subtle", "subtly",
]
STOCK_PHRASES = [
    r"\bplays? an? (crucial|key|vital|pivotal|significant|central|important) role\b",
    r"\b(serves|stands) as an?\b",
    r"\bkey (insight|consideration|factor|aspect)s?\b",
    r"\b(deep|rich) (understanding|history|heritage)\b",
    r"\b(on|in) (a|the|this|your|our) journey\b",
    r"\bensur(e|es|ing) (that )?(a |the )?(smooth|seamless|consistent|robust)\b",
    r"\bwhile (preserving|maintaining|keeping|ensuring|retaining)\b",
    r"\b(clear and concise|fast and reliable|safe and secure|simple and intuitive|clean and maintainable|"
    r"robust and scalable|scalable and maintainable|quick and easy|seamless and intuitive|efficient and effective|"
    r"accurate and reliable|reliable and efficient)\b",
    r"\b(seemed|began|started) to (hover|drift|amplify|settle|fade|shift|blur|soften|tighten|linger)\b",
    r"\b(sarah|marcus) chen\b|\belena vasquez\b|\bokafor\b",
    r"\bthe irony (wasn'?t|was not) lost\b|\bsomething else entirely\b|\bfor a long moment\b",
]

EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002B50\U00002B55\U0001F000-\U0001F2FF]"
)

CLOSER_START = re.compile(
    r"^\s*(overall|in short|in summary|in conclusion|ultimately|all in all|in the end|"
    r"going forward|moving forward|looking ahead|together,|net[- ]net|"
    r"with (this|these) (change|changes|fix|fixes|update|updates)|"
    r"this (change|pr|update|fix|approach) (ensures|means|makes|keeps|brings|gives)|"
    r"the result( is)?\b|bottom line)",
    re.I,
)

EPILOGUE_HEADINGS = re.compile(
    r"^#{1,6}\s*(next steps|future work|looking ahead|conclusion|summary|key takeaways|"
    r"takeaways|why this matters|wrapping up|final thoughts|impact|overview)\s*:?\s*$",
    re.I | re.M,
)


# Claude's intensifiers. One is fine; several in a short text is a pattern.
CLAUDE_WORDS = re.compile(r"\b(actually|genuinely|honestly|precisely|exactly|somehow|truly)\b", re.I)
CLAUDE_OPENER = re.compile(r"^\s*(here'?s|here is|here are|based on|according to)\b", re.I)
ARROWS = re.compile("[\u2192\u21d2\u27f6\u2248\u2500]")
CHANGELOG_HEADING = re.compile(
    r"^#{1,6}\s*(what('?s)? changed (in|since) v\d+|changes (in|since) v\d+|revised( version| draft)?\s*$|"
    r"revision notes|what holds up|what was wrong)",
    re.I | re.M,
)
SMALL_WORDS = {"a", "an", "the", "and", "or", "but", "of", "in", "on", "at", "to", "for", "by", "with", "vs", "via", "from", "as", "is"}


# ---------------------------------------------------------------------------
# Report types
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    severity: str  # "error" | "warn"
    rule: str
    line: int
    excerpt: str
    advice: str = ""


@dataclass
class Report:
    findings: List[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == "warn"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FENCE = re.compile(r"^([ \t]*)(```|~~~).*?^\1\2[ \t]*$", re.S | re.M)
INLINE_CODE = re.compile(r"`[^`\n]+`")
URL = re.compile(r"https?://\S+|www\.\S+")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
# Short quoted spans are mentions (UI strings, error text, someone else's words, dialogue), not the
# writer's own prose, so they are skipped too.
QUOTED = re.compile(r'"[^"\n]{1,120}"|\u201c[^\u201d\n]{1,120}\u201d')
EMPTY_CELL = re.compile(r"(?<=\|)[ \t]*[\u2014\u2013-]+[ \t]*(?=\|)")


def _blank(match: re.Match) -> str:
    # Keep newlines so line numbers stay right.
    return re.sub(r"[^\n]", " ", match.group(0))


def mask_code(text: str) -> str:
    """Blank out code fences, inline code, URLs and HTML comments."""
    text = FENCE.sub(_blank, text)
    # An unclosed fence (common in partial edits): blank to the end.
    m = re.search(r"^[ \t]*(```|~~~)", text, re.M)
    if m:
        text = text[: m.start()] + _blank(re.match(r"(?s).*", text[m.start():]))
    text = INLINE_CODE.sub(_blank, text)
    text = URL.sub(_blank, text)
    text = HTML_COMMENT.sub(_blank, text)
    text = EMPTY_CELL.sub(_blank, text)  # a lone dash marks an empty table cell
    text = QUOTED.sub(_blank, text)
    return text


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def excerpt(text: str, start: int, end: int, width: int = 34) -> str:
    a = max(0, start - width)
    b = min(len(text), end + width)
    s = text[a:b].replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return ("..." if a > 0 else "") + s + ("..." if b < len(text) else "")


SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[\"'(\[]?[A-Z0-9])")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
HEADING = re.compile(r"^\s*#{1,6}\s+")
BOLD_LABEL_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+\*\*[^*\n]{1,60}\*\*\s*[:.\u2014-]?")
BOLD = re.compile(r"(?<!\[)\*\*[^*\n]+\*\*(?!\]\()")
# A comma list of short items ending in "and"/"or". Its item count decides whether it's a triplet.
ITEM = r"[\w'/-]+(?: [\w'/-]+)?"
COMMA_LIST = re.compile(rf"(?:{ITEM}, )+{ITEM},? (?:and|or) {ITEM}")


def triplets(text: str) -> List[str]:
    out = []
    for m in COMMA_LIST.finditer(text):
        s = m.group(0)
        commas = s.count(", ") - (1 if re.search(r", (?:and|or) ", s) else 0)
        if commas + 2 == 3:
            out.append(s)
    return out


# A short sentence standing alone as a paragraph, like "That's it." or "And it works."
DRAMATIC = re.compile(r"^(?!\*\*)[^#/|:\n]{1,40}[.!?]$")
REF_LINE = re.compile(r"^(closes|fixes|resolves|refs?|see|part of|tracked|related|follow-?up|depends|blocked|supersedes|reverts?)\b", re.I)


def prose_blocks(masked: str) -> List[tuple]:
    """(offset, text) for paragraphs of running prose: no headings, lists, tables or quotes."""
    blocks = []
    for m in re.finditer(r"(?:[^\n]*\S[^\n]*(?:\n|$))+", masked):
        lines = [l for l in m.group(0).split("\n") if l.strip()]
        if any(HEADING.match(l) or LIST_ITEM.match(l) or l.lstrip().startswith(("|", ">")) for l in lines):
            continue
        blocks.append((m.start(), " ".join(l.strip() for l in lines)))
    return blocks


def sentences(block: str) -> List[str]:
    return [s for s in SENT_SPLIT.split(block) if len(s.split()) >= 1]


# ---------------------------------------------------------------------------
# The linter
# ---------------------------------------------------------------------------

def lint(text: str, rhythm: bool = True) -> Report:
    """Check text. rhythm=False skips whole-document checks (for diffs and fragments)."""
    rep = Report()
    masked = mask_code(text)
    add = rep.findings.append

    def scan(rule: str, sev: str, pattern, advice: str = "", flags=re.I) -> None:
        rx = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, flags)
        for m in rx.finditer(masked):
            add(Finding(sev, rule, line_of(masked, m.start()), excerpt(masked, m.start(), m.end()), advice))

    for rule, sev, rx, advice in CHAR_RULES:
        scan(rule, sev, rx, advice)
    for p in ATTRIBUTION:
        scan("ai-attribution", "error", p, "remove it")
    for p in CHATBOT_PHRASES:
        scan("chatbot-phrase", "error", p, "cut it; say the actual thing or nothing")
    for p in STRONG_STOCK:
        scan("stock-phrase", "error", p, "say it plainly")
    for p in CONTRAST_REFRAMES:
        scan("contrast-reframe", "warn", p, "state what it is; drop the 'not X' setup")
    for p in SIGNPOSTS:
        scan("signpost", "warn", p, "cut the announcement and just say it")
    scan("colon-reveal", "warn", COLON_REVEAL, "write the sentence without the drumroll")
    scan("ing-tail", "warn", ING_TAIL, "cut the trailing commentary or make it its own claim")
    for p in HEDGE_STACK:
        scan("hedge-stack", "warn", p, "hedge once, where the doubt is real")
    for p in CHAT_CLOSERS:
        scan("chat-closer", "warn", p, "fine in chat, wrong in a document or message to others")
    for p in STOCK_PHRASES:
        scan("stock-phrase", "warn", p, "say what it does")

    # Stock words: one finding per word with a count.
    words_rx = re.compile(r"\b(" + "|".join(re.escape(w) for w in STOCK_WORDS) + r")\b", re.I)
    seen = {}
    for m in words_rx.finditer(masked):
        w = m.group(1).lower()
        if w not in seen:
            seen[w] = [m.start(), m.end(), 0]
        seen[w][2] += 1
    for w, (s, e, n) in seen.items():
        add(Finding("warn", "stock-word", line_of(masked, s), excerpt(masked, s, e) + (f"  (x{n})" if n > 1 else ""),
                    f"'{w}' is an AI favourite; use a plainer or more specific word"))

    hits = CLAUDE_WORDS.findall(masked)
    n_tokens = len(re.findall(r"[A-Za-z0-9']+", masked)) or 1
    if len(hits) >= 2 and (len(hits) >= 3 or len(hits) * 1000 / n_tokens > 3):
        m = CLAUDE_WORDS.search(masked)
        counts = {}
        for h in hits:
            counts[h.lower()] = counts.get(h.lower(), 0) + 1
        add(Finding("warn", "claude-intensifiers", line_of(masked, m.start()),
                    ", ".join(f"{w} x{n}" for w, n in sorted(counts.items(), key=lambda kv: -kv[1])),
                    "Claude leans on these; cut most of them"))

    m = CLAUDE_OPENER.match(masked)
    if m:
        add(Finding("warn", "claude-opener", 1, excerpt(masked, m.start(), m.end()),
                    "Claude's favourite openings; start with the substance"))

    arrows = list(ARROWS.finditer(masked))
    if arrows:
        add(Finding("warn", "arrows", line_of(masked, arrows[0].start()),
                    excerpt(masked, arrows[0].start(), arrows[0].end()) + (f"  (x{len(arrows)})" if len(arrows) > 1 else ""),
                    "arrows and approximately signs in prose are an AI habit; write 'then', 'to' or 'about', and '>' for menu paths"))

    for m in CHANGELOG_HEADING.finditer(masked):
        add(Finding("warn", "changelog-heading", line_of(masked, m.start()), m.group(0).strip(),
                    "hand over the new version; don't narrate the revision"))

    for i, l in enumerate(masked.split("\n"), 1):
        if not HEADING.match(l):
            continue
        words = re.findall(r"[A-Za-z][A-Za-z'-]*", HEADING.sub("", l))
        big = [w for w in words if w.lower() not in SMALL_WORDS]
        if len(words) >= 4 and len(big) >= 3 and all(w[0].isupper() for w in big):
            add(Finding("warn", "title-case-heading", i, l.strip()[:70], "use sentence case for headings"))

    # Emoji at the start of headings or list items.
    for i, l in enumerate(masked.split("\n"), 1):
        body = LIST_ITEM.sub("", HEADING.sub("", l)).lstrip()
        if (HEADING.match(l) or LIST_ITEM.match(l)) and EMOJI.match(body):
            add(Finding("warn", "emoji-marker", i, l.strip()[:70], "drop emoji used as bullets or heading decoration"))

    lines = masked.split("\n")
    bold_items = [i for i, l in enumerate(lines, 1) if BOLD_LABEL_ITEM.match(l)]
    if len(bold_items) >= 3:
        add(Finding("warn", "bold-label-list", bold_items[0], lines[bold_items[0] - 1].strip()[:70],
                    f"{len(bold_items)} list items open with a bold label; write sentences or plain items"))

    for m in EPILOGUE_HEADINGS.finditer(masked):
        add(Finding("warn", "epilogue-heading", line_of(masked, m.start()), m.group(0).strip(),
                    "a wrap-up section; keep it only if the format asks for it or it has real actions with owners"))
    if re.search(r"^#{1,6}\s*summary\s*$", masked, re.I | re.M) and re.search(r"^#{1,6}\s*test plan\s*$", masked, re.I | re.M):
        add(Finding("warn", "default-pr-template", 1, "## Summary ... ## Test plan",
                    "this is Claude Code's stock PR layout; open with a plain summary and an example instead"))

    # Whole-document checks.
    words = re.findall(r"[A-Za-z0-9']+", masked)
    n_words = len(words)
    blocks = prose_blocks(masked)
    sent_lens = [len(s.split()) for _, b in blocks for s in sentences(b)]
    heads = [l for l in lines if HEADING.match(l)]
    rep.stats = {
        "words": n_words,
        "sentences": len(sent_lens),
        "paragraphs": len(blocks),
        "headings": len(heads),
        "list_items": sum(1 for l in lines if LIST_ITEM.match(l)),
        "bold_spans": len(BOLD.findall(masked)),
        "em_dashes": len(re.findall("[\u2014\u2015]", masked)),
        "semicolons": masked.count(";"),
    }
    if sent_lens:
        mean = statistics.mean(sent_lens)
        sd = statistics.pstdev(sent_lens) if len(sent_lens) > 1 else 0.0
        rep.stats.update({
            "sentence_len_mean": round(mean, 1),
            "sentence_len_sd": round(sd, 1),
            "sentence_len_cv": round(sd / mean, 2) if mean else 0.0,
            "share_12_to_25_words": round(sum(12 <= n <= 25 for n in sent_lens) / len(sent_lens), 2),
        })

    if not rhythm:
        return rep

    first = next((l for l in lines if l.strip()), "")
    if re.match(r"^\s*#\s+\S", first) and n_words < 300:
        add(Finding("warn", "title-heading", 1, first.strip()[:70],
                    "a title heading on a short piece; the subject line or the first sentence can carry it"))

    if n_words and len(heads) >= 2 and n_words < 250:
        add(Finding("warn", "headings-in-short-text", line_of(masked, masked.find(heads[0])), heads[0].strip(),
                    f"{len(heads)} headings in {n_words} words; short text reads better as plain paragraphs"))

    if len(sent_lens) >= 8:
        cv = rep.stats["sentence_len_cv"]
        band = rep.stats["share_12_to_25_words"]
        if cv < 0.35:
            add(Finding("warn", "uniform-sentences", 1, f"sentence length {rep.stats['sentence_len_mean']} +/- {rep.stats['sentence_len_sd']} words (cv {cv})",
                        "lengths are too even; mix short sentences with long ones"))
        elif band > 0.7:
            add(Finding("warn", "mid-length-monotony", 1, f"{int(band * 100)}% of sentences are 12-25 words",
                        "almost every sentence is medium length; vary it"))

    para_sents = [len(sentences(b)) for _, b in blocks]
    if len(para_sents) >= 4 and all(2 <= n <= 4 for n in para_sents):
        add(Finding("warn", "uniform-paragraphs", 1, f"{len(para_sents)} paragraphs, each {min(para_sents)}-{max(para_sents)} sentences",
                    "paragraphs are all the same size; let some be one line and some run long"))

    one_liners = [b for _, b in blocks if DRAMATIC.match(b) and not REF_LINE.match(b)]
    if len(one_liners) >= 3:
        add(Finding("warn", "dramatic-one-liners", 1, " / ".join(one_liners[:3]),
                    "several punchy one-line paragraphs; keep at most one"))

    threes = triplets(masked)
    if len(threes) >= 3 and n_words and len(threes) * 1000 / n_words > 2:
        add(Finding("warn", "groups-of-three", 1, "; ".join(threes[:3]),
                    f"{len(threes)} lists of exactly three; use the real number of items"))

    if n_words >= 120 and rep.stats["semicolons"] * 100 / n_words > 1:
        add(Finding("warn", "semicolons", 1, f"{rep.stats['semicolons']} semicolons in {n_words} words",
                    "lots of semicolons; if they replaced dashes, recast those sentences instead"))

    if blocks:
        off, last = blocks[-1]
        if CLOSER_START.match(last):
            add(Finding("warn", "summary-closer", line_of(masked, off), excerpt(last, 0, min(len(last), 60), 0),
                        "the last paragraph restates or moralizes; end on the last real point"))
    return rep


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_findings(findings: Iterable[Finding], limit: Optional[int] = None) -> List[str]:
    out = []
    for i, f in enumerate(findings):
        if limit is not None and i >= limit:
            break
        tag = "ERROR" if f.severity == "error" else "warn "
        out.append(f"{tag} {f.rule} (line {f.line}): {f.excerpt}" + (f"  -> {f.advice}" if f.advice else ""))
    return out


def format_report(rep: Report, name: str = "") -> str:
    head = f"{name}: " if name else ""
    lines = [f"{head}{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)"]
    lines += ["  " + l for l in format_findings(rep.errors + rep.warnings)]
    s = rep.stats
    if s.get("sentences"):
        lines.append(
            f"  stats: {s['words']} words, {s['sentences']} sentences in {s['paragraphs']} prose paragraphs, "
            f"sentence length {s['sentence_len_mean']} +/- {s['sentence_len_sd']} (cv {s['sentence_len_cv']}), "
            f"em dashes {s['em_dashes']}, semicolons {s['semicolons']}, bold {s['bold_spans']}"
        )
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    strict = "--strict" in argv
    if not args or "--help" in argv or "-h" in args:
        print(__doc__.strip())
        return 2 if not args else 0
    worst = 0
    reports = {}
    for path in args:
        try:
            text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        except OSError as e:
            print(f"{path}: {e}", file=sys.stderr)
            return 2
        rep = lint(text)
        reports[path] = rep
        if rep.errors or (strict and rep.warnings):
            worst = 1
    if as_json:
        print(json.dumps({p: {"findings": [asdict(f) for f in r.findings], "stats": r.stats}
                          for p, r in reports.items()}, indent=2))
    else:
        print("\n\n".join(format_report(r, p if len(reports) > 1 or p != "-" else "") for p, r in reports.items()))
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
