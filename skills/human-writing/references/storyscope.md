# What the StoryScope paper found

Source: Jenna Russell, Rishanth Rajendhran, Chau Minh Pham, Mohit Iyyer, John Wieting. "StoryScope: Investigating idiosyncrasies in AI fiction". University of Maryland and Google DeepMind, arXiv 2604.03136 (v6). https://arxiv.org/abs/2604.03136. Code and data: https://github.com/jenna-russell/storyscope

## What they did

They took 10,272 human short stories (from Books3), worked backwards to a writing prompt for each, and had five models write a story from the same prompt: Claude Sonnet 4.6, GPT-5.4, Gemini 3 Flash, DeepSeek V3.2 and Kimi K2.5. That gave 61,608 stories averaging about 4,750 words. An LLM pipeline then scored every story on 304 narrative features (plot, characters, time, setting, revelation, perspective and so on), and gradient-boosted classifiers tried to tell the sources apart.

Keep in mind what this is. It studies fiction, and it studies narrative choices, deliberately leaving out sentence-level style: 39 style features exist but sit outside the main model. So it says a lot about the shape of AI writing and little about word choice. The word-level tells it mentions (em dashes, "delve", "tapestry") come from the earlier work it cites.

## Headline results

- Narrative features alone separate human from AI stories at 93.2% macro-F1. Adding the style features only takes that to 96.0%. Text classifiers that see the raw words (ModernBERT, stylometry, TF-IDF) reach 99.5 to 99.9%.
- Naming the exact source (human or one of the five models) works at 68.4% from narrative features and 77.3% with style.
- Thirty "core" features carry most of the human-versus-AI signal (84.8% F1 on their own).
- Surface editing doesn't help much. The authors ran an editing pass that removes clichés, redundant exposition, purple prose and similar artifacts (the LAMP method) over 278 Gemini stories. The narrative detector still caught them at 93.9% F1, against 95.5% before editing.
- AI stories sit in one tight cluster. Human stories are spread wider and are rarer: mean rarity percentile 0.71 against 0.49, and the human version is the rarest of the six for 57.8% of prompts (chance would be 16.7%).

## The 30 core features (human vs. AI average across all five models)

Scales run 1 to 5 unless marked; percentages are how often the option was chosen.

| Theme | Feature | Human | AI |
|---|---|---|---|
| AI spells out the meaning | Thematic explicitness and moralizing | 3.28 | 3.94 |
| | Moral or philosophical weighting | 3.26 | 3.68 |
| | Thematic unity | 4.41 | 4.74 |
| | Narrator comments on the theme outright | 52% | 77% |
| | Dialogue used for philosophical debate | 34% | 59% |
| | References are vague echoes, not named works | 50% | 72% |
| AI over-writes body and senses | Emotion shown through body sensations | 38% | 81% |
| | Setting mirrors a character's mood | 3.58 | 4.07 |
| | Environmental emphasis | 2.83 | 3.21 |
| | Smell among the main senses used | 57% | 82% |
| | Sensory density | 3.66 | 3.93 |
| | Depth of access to characters' inner life | 3.67 | 3.93 |
| AI keeps to one straight line | One continuous cause-and-effect chain | 3.92 | 4.20 |
| | Spatial detail (ordinal) | 2.27 | 2.53 |
| | Resolution comes from the protagonist's choice | 46% | 69% |
| | Main character introduced by description | 30% | 52% |
| | No subplots | 57% | 79% |
| | Resolved through inner understanding or acceptance | 27% | 47% |
| | Opening grounds the reader in a place (ordinal) | 2.12 | 2.33 |
| | Build-up before the threat arrives | 2.76 | 2.99 |
| Humans name their sources | References name specific works or authors | 47% | 24% |
| | Balanced mix of named and implicit references | 37% | 16% |
| Humans talk to the reader | Fourth-wall permeability (ordinal) | 0.67 | 0.39 |
| | Direct address to the reader (ordinal) | 0.28 | 0.07 |
| Humans play with time | Earlier scenes reread after a surprise | 3.28 | 2.95 |
| | Chronological jumps | 2.40 | 2.12 |
| | Time jumps used to hold back a reveal | 1.96 | 1.68 |
| | Flashbacks and flash-forwards | 2.58 | 2.31 |
| Human stories range wider | Number of distinct locations (ordinal) | 1.34 | 1.08 |
| | Share of dialogue against narration | 2.95 | 2.70 |
| | Subplots that echo the theme | 42% | 21% |
| | Protagonist's choices are morally mixed | 59% | 38% |
| | Emotions named outright ("she was afraid") | 29% | 8% |

## Claude's fingerprint

Claude was the most distinctive of the five models (per-class F1 89.3% with style, 77.1% without; only the human class scored higher). The paper sums it up as "Claude keeps it cool":

- Event intensity escalates less than in any other source. Strength of escalation is Claude's single most distinctive feature.
- Its narrative voice is the most uniform.
- It honours and extends convention rather than subverting it: 62% of Claude stories take that "reverent" stance, against 39 to 56% for the others.
- It favours epilogues and flash-forward endings, and quiet endings over "avalanche" endings.
- It avoids dream sequences.
- Its other top fingerprints are event-type diversity and an uncanny or haunted setting mood. The paper lists 21 more only by name: event density, conflict modality, relationship trajectory, heteroglossia (how many distinct voices a text carries) and closure among them.

Claude also ran long: 6,817 words on average against a mean target of 6,242. GPT ran over too, while Gemini, DeepSeek and Kimi came in about 3,000 words short. Claude was still the closest to the requested length (38% of its stories within 10%).

For comparison, GPT leans on gossip and rumour and on looking back from years later, Gemini on tidy endings, long denouements and bleak settings, DeepSeek on front-loading context, and Kimi sits at the generic middle.

## What carries over to non-fiction

The paper doesn't test PRs, docs or emails. These are translations, and they're judgment calls:

| Finding in fiction | In everyday writing |
|---|---|
| States the theme or moral (77% vs 52%) | Cut "this matters because", "the key insight", the closing moral. Let the facts carry it. |
| Single causal chain, no subplots, tidy resolution | Leave real loose ends visible. Say what's still unknown. |
| Linear telling, few time jumps | Lead with the outcome, then give only the backstory that's needed. |
| Vague allusions; avoids naming real works, brands, places | Name the file, version, PR, command, error, person, number. |
| Rarely addresses the reader | Write to "you"; ask for what you need. |
| Emotion through body sensations, rarely named | If a feeling matters, name it plainly. Skip the imagery. |
| Description-first introductions | Introduce things by what they do. |
| Heavy build-up before the stakes | Get to the point in the first sentence or two. |
| Claude: flat escalation, uniform voice | Let urgency show when it's urgent. Mix registers; quote others. |
| Claude: convention-following | Don't default to the template. Fit form to content. |
| Claude: epilogues, quiet endings | No wrap-up section. Stop at the last real point. |
| AI converges on one narrow region | Avoid the first, most expected shape for every piece. |
