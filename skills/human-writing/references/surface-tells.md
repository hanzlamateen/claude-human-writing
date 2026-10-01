# Word, punctuation and formatting tells

StoryScope (see [storyscope.md](storyscope.md)) deliberately set word-level style aside. This page collects the word-level evidence from other sources, with Claude-specific findings first. Tags: [Claude] means measured on Claude, [AI] means measured across models, [human] means something people do more.

One finding from the general sources is worth repeating before the list. Most published word lists were built on ChatGPT output, and Claude barely uses those words. On EQ-Bench's slop score, which is built from a GPT-derived list, Claude models score lowest of all the models tested. A list of GPT words will miss Claude.

## Claude-specific

- Em dashes. Pangram counts 32 em dashes per 10,000 words in Anthropic models' text against 5 in human text. The Economist (July 2026) found that "only Claude uses more em-dashes than human writers", with ChatGPT now using fewer than anyone. Claude writes them unspaced, like—this. [Claude]
- Openers and reference phrases. In Sun et al.'s study of five chat models, Claude preferred "here", "according to" and "based on", and pointed back at its input with "according to the text" or "based on the text". [Claude]
- Intensifiers. In a tally of the public EQ-Bench slop-score outputs (Claude Sonnet 4 and 4.5 fiction against nine other models; a tally, not a published result), Claude used "actually", "precisely" or "exactly", "somehow" and "genuinely" at several times the other models' rates. [Claude]
- Fiction phrases from the same outputs: "the irony wasn't lost on", "something else entirely", "for a long moment", "laughed, a real one". Stock character names: Sarah or Marcus Chen, Elena Vasquez, Priya, Okafor. Worth checking in examples and test data too. [Claude]
- Title headings. Claude Sonnet 4.5 put a heading on all 150 stories in that set, 71% of them in Title Case. ChatGPT-4o put one on none. [Claude]
- Formatting. Sun et al. found Claude 3.5 used less bold and fewer headers than the other models, preferring plain numbered lists and bullets. Claude Code is different: of 24 PR descriptions written with it in September 2026 (our own), 20 had runs of bold-label bullets. [Claude]
- "You're absolutely right!" has its own Claude Code issue (anthropics/claude-code#3382, 870 thumbs-up). [Claude]
- Anecdotal "Claudish" from one heavy Claude Code user: "The one thing you need to...", "It's a real X, not Y", "That's precisely the X you've encountered", "Honest caveat:", "here's the smoking gun", and revisions written as change logs ("What changed in v3", "What holds up / what was wrong"). [Claude, anecdotal]
- Claude reads as dense. Expert readers in one study called it "so strictly formal, so tight and dense with wordage". The "Claudish" post adds noun stacks like "can't wedge the deep-link". [Claude]

## Across models

- Groups of three: 19 per 10,000 words in AI text against 5 in human text (Pangram). [AI]
- Arrows: "→" appears at 48 times the human rate (Pangram). Use words: "then", "to", "becomes". [AI]
- Markdown: bold at 43 times and headers at 23 times the human rate; the ✅ emoji at 167 times and 🚀 at 26 times (Pangram). [AI]
- Grammar (Reinhart et al., PNAS 2025, on GPT-4o, GPT-4o-mini and Llama 3; no Claude): present-participle clauses at 2 to 5 times the human rate, nominalizations about 2 times, "X and Y" phrasal pairs about 2 times, and agentless passives about half as often. Base models matched humans, so the shift comes from instruction tuning. [AI]
- The Economist: models write longer sentences of more uniform length, "'and' is their most overused word", and paragraphs come out "blocky". They use fewer commas and semicolons than people "and hardly any parentheses". [AI]; parentheses are [human]
- "Not X but Y" constructions: Claude Sonnet 4.5 used them at about 4 times the human rate in one dataset, though GPT-4o used them more. Claude often splits the move across two sentences: "This wasn't X. This was Y." [AI]
- "Serves as", "stands as", "features" and "offers" in place of plain "is" and "has". Human text has more "is" and "has", more plain verbs and more small hedges ("very", "perhaps", "tends to"). [AI]
- Trailing "-ing" commentary: ", highlighting...", ", ensuring...". Professional editors deleted these outright. [AI]
- Edit summaries and commit messages: stacked assurances ("improved clarity, flow, and readability") and "while preserving...". [AI]
- Biomedical abstracts after ChatGPT (Kobak et al., Science Advances 2025): "delves" at 28 times its old rate, "underscores" 13.8, "showcasing" 10.7, then "meticulously", "intricate", "commendable", "garnered" and "realm". Biggest absolute gains: "potential", "findings", "crucial", "additionally". These are ChatGPT-era words. [AI]
- What professional writers fixed in AI fiction (Chakrabarty et al., CHI 2025, the LAMP corpus): awkward word choice (28% of edits), poor sentence structure (20%), unnecessary exposition (18%), cliché (17%), then purple prose, missing specifics and tense slips. Typical fixes: "seemed to hover" became "hovered", "began to drift" became "drifted", a long ornate sentence became "She cried." The writers found no real quality difference between Claude 3.5, GPT-4o and Llama 3.1. [AI]
- What makes readers call text slop (Shaib et al. 2025): relevance mattered most, then information density and tone. Readers agreed on which spans were bad but not on whether a whole text was slop. [AI]

## What doesn't survive as advice

- Curly quotes are a ChatGPT and DeepSeek habit, not Claude's (0% in the tally above).
- "Delve" and "tapestry" barely occur in Claude's output. They're still worth avoiding, but they won't catch Claude.
- No source supports "AI writes short punchy sentences". The measured pattern is the opposite: long, even sentences.
- Rewording doesn't hide the source. Sun et al.'s classifier still named the model 91.4% of the time after paraphrasing and 91.8% after translation (chance: 20%). That fits StoryScope: structure gives text away.

## Sources

- Sun et al. 2025, "Idiosyncrasies in Large Language Models". <https://arxiv.org/abs/2502.12150>
- Pangram Labs, "Signs of AI writing". <https://www.pangram.com/signs-of-ai-writing>
- The Economist, "How to spot AI writing", 30 July 2026, quoted via <https://daringfireball.net/linked/2026/08/11/economist-ai-writing>
- EQ-Bench creative writing and slop score. <https://eqbench.com/creative_writing.html>, <https://github.com/sam-paech/slop-score>
- Reinhart et al. 2025, "Do LLMs write like humans?", PNAS. <https://doi.org/10.1073/pnas.2422455122>
- Kobak et al. 2025, "Delving into LLM-assisted writing in biomedical publications through excess vocabulary", Science Advances. <https://doi.org/10.1126/sciadv.adt3813>
- Chakrabarty et al. 2025, "Can AI writing be salvaged?" (LAMP). <https://arxiv.org/abs/2409.14509>
- Shaib et al. 2024, syntactic templates in generated text. <https://arxiv.org/abs/2407.00211>
- Shaib et al. 2025, measuring "AI slop" in text. <https://arxiv.org/abs/2509.19163>
- Expert readers on AI text. <https://arxiv.org/abs/2501.15654>
- Wikipedia, "Signs of AI writing". <https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>
- "Claudish", slhck.info, June 2026. <https://slhck.info/software/2026/06/22/claudish.html>
- "You're absolutely right" issue. <https://github.com/anthropics/claude-code/issues/3382>
