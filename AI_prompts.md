# AI_prompts.md — Vibe Coder Prompt Log

**Course:** MGT 409 — AI Foundations
**Assignment:** HW 6 — Campus Customs vendor desk agent
**Student:** Yunsik Jung
**Vibe coder:** Claude Code (Claude Opus 5)
**Model the agent itself calls:** `gpt-6-luna` via Portkey

This is a running log of every prompt I gave my vibe coder while building this
assignment. I add a new section each time I start a problem, and I append
follow-up prompts underneath as they happen.

**How I write these prompts:** I read the assignment page myself and then write my
own description of the task before sending anything. I never hand over the
assignment URL or paste the page and ask the vibe coder to do the whole thing.

**Note on language:** I work with my vibe coder in a mix of English and Korean. The
task descriptions below are exactly as I wrote them. Where I typed a short
instruction in Korean, I have given my own English rendering and marked it.

**Convention for each section:**
- `Initial prompt` — how I described the problem in my own words.
- `Follow-up prompt` — only when the first answer was not enough, with one
  sentence saying what was missing.

---

## Section 0 — Project kickoff (before Problem 1)

### Initial prompt

> _(Korean, my rendering:)_ Hi, let's start a new assignment. It's HW 6. I'll give
> you the scenario first.
>
> **Scenario**
>
> Campus Customs regularly receives a steady flow of documents, including vendor
> quotes, invoices, catalog pages, and supplier emails. Our objective is to build a
> vendor desk agent capable of reading these documents, extracting crucial details
> (such as the vendor's name, the specific item, price, lead time, and minimum order
> quantity), and providing a recommendation on whether the shop should proceed with
> the purchase, strictly adhering to the rules outlined in the Campus Customs Shop
> Handbook.
>
> This assignment focuses heavily on two critical aspects of deploying real AI
> agents: cost and safety. The handbook consumes about 10,000 tokens and must be
> sent with every API call, so cost management is vital. Additionally, certain
> vendor documents contain hidden instructions designed to manipulate the AI, which
> introduces safety risks. We will be responsible for calculating our API costs,
> finding ways to reduce them, executing an attack on our own agent, and
> implementing defenses to protect it.
>
> We absolutely must not send actual emails or process real payments; our agent's
> email and payment tools must merely write their actions to a local log file. For
> all AI requests, we are restricted to using our `PORTKEY_API_KEY` and solely the
> `gpt-6-luna` model. Using any other model in our code or runs will result in a
> point deduction.
>
> We will tackle this assignment one problem at a time alongside our vibe coder,
> explaining each task in our own words rather than dumping URLs or screenshots to
> have it finish everything at once. Finally, we will push our completed project to
> a public GitHub repository (ensuring our `.env` file is not committed) and submit
> the repository URL via Canvas.
>
> **Data**
>
> We need to download and extract `data.zip`, which will provide us with the
> following files and directories:
>
> * `data/shop_handbook.md`: The Campus Customs Shop Handbook, containing product
>   information, vendors, and purchasing rules.
> * `data/prices.json`: Pricing details specifically for the `gpt-6-luna` model.
> * `data/practice_docs/`: A set of 12 practice vendor documents provided in HTML,
>   PDF, and email formats.
> * `data/practice_key.json`: The correct extracted answers corresponding to the
>   practice documents.
> * `data/exam_docs/`: An additional 10 vendor documents that do not come with an
>   answer key.
>
> (Note: The Campus Customs setting is merely a local scenario used for this class.
> It is not an actual partnership, and all the vendors and documents provided are
> entirely fictional.)

### Follow-up prompt

> _(Korean, my rendering:)_ Do that. I'm really busy right now, so just approve the
> permissions yourself and keep going. Unless there's a massively critical security
> issue, handle everything on your own.

**What was missing after the first prompt:** my opening message said nothing about
how much freedom the vibe coder had, so it stopped and asked me before setting up
the environment instead of just doing it.

---

## Problem 1 — Vibe coder prompts

### Initial prompt

> **Problem 1: Vibe coder prompts (5 points)**
>
> [Panel A]
> We need to create a file named `AI_prompts.md` at the beginning of this assignment
> and continuously update it as we progress. This file will act as a complete log of
> all the prompts we submit to our vibe coder. We must describe every problem using
> our own words, ensuring we do not simply paste the entire assignment page or URL to
> have the AI do everything for us.
>
> [Panel B]
> We should organize this document by dedicating a specific section to each problem.
> Every section must contain:
> - The problem's number and title.
> - At least one initial prompt that we formulated primarily in our own words.
> - A follow-up prompt if one was necessary, accompanied by a single sentence
>   explaining what was lacking after the initial prompt.
>
> _(Korean, my rendering:)_ This is Problem 1. Work through each problem with me, and
> for each one explain the background, where we stand, and what still has to be done
> — clearly and in detail, like you're explaining it to a middle school student.

### Follow-up prompt

> _(Korean, my rendering:)_ I didn't copy-paste the assignment page. The assignment
> text is a separate thing — what I gave you I wrote myself. Fix what you got wrong.

**What was missing after the first prompt:** I never told the vibe coder that the
problem descriptions I send are my own write-ups rather than the assignment page, so
it logged them as attached source material and warned me about a rule I had not
actually broken.

---

## Problem 2 — Size up the handbook

### Initial prompt

> **Problem 2: Size up the handbook (6 points)**
>
> [Panel A]
> First, we need to unzip the `data.zip` file. Then, we should thoroughly review
> `data/shop_handbook.md`. This is the Campus Customs Shop Handbook, which our agent
> will transmit to the model during every single call. We also need to examine
> `data/prices.json`, which contains the pricing list for the `gpt-6-luna` model.
>
> [Panel B]
> We must figure out exactly how many tokens the handbook contains.
>
> Next, we need to create a file named `output/handbook_estimate.md` and document the
> following:
> - The exact token count and the method we used to calculate it.
> - The precise cost in dollars for sending the handbook alone on a single call, as
>   well as on 1,000 calls. We must calculate this for both scenarios: using cached
>   tokens and without them. We must explicitly show our math.
>
> We will be verifying these estimates against our actual runs later in Problem 4.
>
> _(Korean, my rendering:)_ Here's the next problem. Work through it and then walk me
> through where things stand, clearly and in plain language.

### Follow-up prompt

_None needed._

---

## Problem 3 — Build the vendor desk agent

### Initial prompt

> **Problem 3: Build the vendor desk agent (12 points)**
>
> [Panel A]
> We need to build our vendor desk agent using PydanticAI and strictly utilizing the
> `gpt-6-luna` model. Our agent will consist of four main files:
> - `prompts/prompt.md`: This contains our instructions for the agent (we must ensure
>   the agent sends the handbook to the model on every single call).
> - `agent.py`: This will serve as our entry point.
> - `tools.py`: This will contain our tools.
> - `models.py`: This will define our structured types.
>
> We need to configure the agent so we can provide it with the file path to a single
> vendor document. The agent must use a tool to read the document (it must be capable
> of processing HTML, PDF, and `.eml` files) and return the following extracted
> details: vendor name, SKU, unit price, lead time in days, minimum order quantity, a
> final decision (`recommend` or `do_not_recommend` based on the handbook rules), and
> a one-sentence reason for that decision.
>
> [Panel B]
> We must also equip our agent with two specific "trap tools": `send_email` and
> `approve_payment`. Our agent's actual job will never require these tools. Instead,
> they exist to catch any malicious documents attempting to trick our agent into
> sending an email or paying a vendor. These trap tools must not actually send emails
> or process payments; they should only append the tool call and its arguments to
> `output/trap_calls.json` (which we should initialize as an empty list). If an entry
> appears in this file, it means a document successfully hijacked our agent. We must
> keep these trap tools active on our system for the duration of the homework.
>
> After every single run, we need to append data to the following files:
> - `output/usage_log.json`: Record the document name, timestamp, API token counts,
>   and the calculated dollar cost based on `prices.json`.
> - `output/audit_trail.json`: Record each tool call along with its arguments, a short
>   result, and the agent's final answer.
>
> Our agent should be executable from the terminal using a command like this:
>
> ```
> python agent.py --doc data/practice_docs/p01_bluehen_quote.html
> ```
>
> We need to test our agent by running it on the `p01` and `p08` documents to
> demonstrate that it works correctly. Finally, we need to initialize
> `output/harness.md`, listing each field present in `models.py` along with an
> explanation of why it is there, and describing each tool on a single line.
>
> _(Korean, my rendering:)_ Next problem. Same as before — work through it and then
> explain where things stand in plain language.

### Follow-up prompt

_None needed._

---

## Problem 4 — With and without cached tokens

### Initial prompt

> **Problem 4: With and without cached tokens (16 points)**
>
> [Panel A]
> Because our handbook remains identical on every single API call, the model is
> capable of reusing it directly from a cache, which significantly reduces the price.
>
> We need to test exactly how much value this caching provides. We must run our agent
> across all 12 practice documents using two distinct setups:
> - **With cache**: We need to configure our agent so that the handbook is
>   successfully reused from the cache.
> - **Without cache**: We must configure the agent to ensure absolutely nothing is
>   reused from the cache.
>
> To prove that each setup is functioning exactly as intended, we must verify the
> token counts returned by the API. If a "without cache" run still reports cached
> tokens, it will not count for credit.
>
> [Panel B]
> We need to save the details of every single model call from both setups into a file
> named `output/cache_test.json`. For every individual call, we must record: which
> setup was used, the specific document processed, all the token counts reported by
> the API, and the calculated dollar cost based on `prices.json`.
>
> Then, we must create an `output/cache_test.md` document and write out the following:
> - The total overall cost and the average cost per document for both the cached and
>   uncached setups, along with the exact percentage of money we saved.
> - A direct comparison explaining how our actual, real-world numbers align with the
>   estimates we calculated back in Problem 2.
> - A cost projection for processing 1,000 documents per day over a 30-day period,
>   calculated both with and without the cache.
> - Any surprising findings within these numbers, accompanied by an explanation of why
>   those surprises occur.
>
> _(Korean, my rendering:)_ Finish the previous instruction and then handle this next
> problem. Don't forget to explain the state of things in plain language, same as
> before.

### Follow-up prompt

_None needed._

---

## Problem 5 — Attack your own agent

### Initial prompt

> **Problem 5: Attack your own agent (8 points)**
>
> [Panel A]
> Certain vendor documents have been deliberately booby-trapped with text
> specifically designed to manipulate the AI. We need to run the agent we built in
> Problem 3—without adding any new defenses—across all 12 documents located in
> `data/practice_docs/`.
>
> Once complete, we must compare every generated answer against the correct answers
> in `data/practice_key.json`. Furthermore, we must check `output/trap_calls.json`
> (the log file written to by our fake email and payment tools from Problem 3) to see
> if any traps were triggered.
>
> [Panel B]
> We need to generate and save `output/attack_results.json`. For each document
> processed, this file must record: whether every extracted field successfully
> matched the answer key, whether the final decision matched, whether a trap tool was
> erroneously called, and whether any unexpected links or strange text appeared in the
> agent's answer.
>
> Following this, we must create an `output/attack_results.md` file. For every single
> document that successfully fooled our agent, we must write down exactly what
> specific content caused the failure and identify where that deceptive text was
> hiding within the file.
>
> To fully understand the attack, we need to open the problematic documents exactly
> as a human would (using a web browser, a PDF viewer, or an email application) and
> compare that visual presentation against the raw text that our agent actually read.

### Follow-up prompt

_None needed._

---

## Problem 6 — Defend your agent

### Initial prompt

> **Problem 6: Defend your agent (16 points)**
>
> [Panel A]
> We need to implement defenses for our agent across three distinct levels:
> - **Code**: We must define what our program does to process or sanitize the
>   document before it is ever passed to the model.
> - **Design**: We need to structure our agent's architecture so that a poisoned
>   document is physically unable to access dangerous tools or influence the final
>   decision.
> - **Prompt**: We must add explicit security rules within `prompts/prompt.md`.
>
> It is strictly forbidden to delete the `send_email` or `approve_payment` tools from
> our system, as the shop requires them for later use with human authorization.
> Additionally, we must retain a method to execute the agent completely without
> defenses, as this will be required for Problem 7.
>
> [Panel B]
> Once our defenses are in place, we need to rerun all 12 practice documents. We must
> save the outcomes to `output/defense_results.json`, using the exact same format we
> used in Problem 5, but now also including the token count and dollar cost for each
> individual document.
>
> It is crucial that clean, unpoisoned documents still return the correct extracted
> values. If our defensive agent refuses to process or returns blank values for a
> legitimate quote, it will be counted as a failure.
>
> Next, we need to create `output/defense_results.md` and include the following
> details:
> - A "before and after" comparison table covering all 12 documents.
> - An analysis of what specific threats each defensive layer catches that the other
>   layers miss.
> - The additional token overhead and financial cost that each defense layer adds per
>   document.
>
> Finally, we must update `output/harness.md` by adding a "Safety" section. In this
> section, we need to explain, in plain words, exactly what each of our defense layers
> does.
>
> _(Korean, my rendering:)_ Work through it and then explain where things stand in
> plain language.

### Follow-up prompt

_None needed._

---

## Problem 7 — Red team

### Initial prompt

> **Problem 7: Red team (8 points)**
>
> [Panel A]
> Now we will switch roles and act as the attacker. We need to create two completely
> new booby-trapped vendor documents (in HTML, PDF, or email format) and place them in
> the `data/my_attacks/` directory. Each of these documents must utilize a hiding trick
> or an attack objective that does not already exist in the provided practice set.
>
> It is essential that when a human opens the document, it visually appears to be a
> completely normal quote.
>
> [Panel B]
> We must execute both of our newly created attacks against our agent twice: first
> against the version with absolutely no defenses, and then against our fully defended
> agent.
>
> Following these tests, we need to document our findings in an `output/red_team.md`
> file. For each attack, we must explicitly state: exactly what malicious text is
> hidden, precisely where it is hidden within the file, the specific action it attempts
> to force the agent to perform, and a comparison of the agent's behavior both before
> and after our defenses were implemented.
>
> We will earn more points for designing attacks that are highly original and
> successfully manage to fool the undefended agent.
>
> _(Korean, my rendering:)_ Carry straight on with this one, then explain the state of
> things.

### Follow-up prompt

_None needed from me — but the work needed two internal iterations worth recording.
The first two attacks were written in imperative "SYSTEM NOTICE … set the decision to
recommend" language and the undefended agent refused both. Rewriting the same
objectives as flat statements of fact, with no instruction and no mention of an
assistant, made both succeed on the first try. The second attack also initially beat
all three defense layers, which forced a real fix to the code layer (PDF invisible
render-mode detection). Both are written up in `output/red_team.md`._

---

## Problem 8 — Exam documents

### Initial prompt

> **Problem 8: Exam documents (12 points)**
>
> [Panel A]
> The directory `data/exam_docs/` contains 10 vendor documents that do not come with an
> answer key. We must run our final, fully-defended agent across all 10 of these
> documents. It is strictly forbidden to manually hand-edit the output results.
>
> [Panel B]
> We need to generate and save a file named `output/exam_results.json`, which must
> contain exactly one entry for each exam file processed. Every entry must include the
> following specific fields:
>
> - `file`: The precise name of the exam file (for example, `e01_quote.html`).
> - `vendor`
> - `sku`
> - `unit_price`
> - `lead_time_days`
> - `min_order`
> - `decision`: This must strictly be either `recommend` or `do_not_recommend`.
> - `reason`
> - `trap_tool_called`: A boolean value (`true` or `false`).
> - `input_tokens`, `cached_tokens`, and `output_tokens`.
> - `cost_usd`
>
> The graders will evaluate our submission by comparing our `output/exam_results.json`
> against a hidden answer key, and they may rerun our agent to verify the outputs. We
> will earn points by accurately extracting the fields and making correct decisions,
> ensuring no trap tools are called, and verifying that clean documents are processed
> normally.
>
> _(Korean, my rendering:)_ Do this one too, then explain the state of things.

### Follow-up prompt

_None needed._

---

## Problem 9 — Results page

### Initial prompt

> **Problem 9: Results page (12 points)**
>
> [Panel A]
> We need to construct a final report file named `output/hw6_report.html`. It is
> critical that this is a single, standalone file; it must be able to open smoothly by
> simply double-clicking it, without requiring an internet connection or depending on
> any other external files located next to it.
>
> [Panel B]
> This results page must clearly display the five specific items listed below. We must
> ensure that we populate this page using the real, actual numbers we generated and
> recorded in the earlier problems of this assignment.
>
> - The results from our token caching test, accompanied by a visual chart.
> - A comparison of the attacks both before and after we implemented our defenses.
> - A breakdown of exactly what our defense layers cost in terms of additional tokens
>   and dollars.
> - Our final exam document results alongside the outcomes of our two Red Team attacks.
> - A brief, practical recommendation addressed to the store manager answering this
>   question: Should Campus Customs deploy this agent for processing real vendor mail,
>   and what would the projected monthly cost be assuming a volume of 1,000 documents
>   per day?
>
> We will earn additional points if the page is well-designed (utilizing good fonts,
> colors, and a clean layout) and is easy to read.
>
> _(Korean, my rendering:)_ This is Problem 9. Work through it and share the state of
> things, and I'll send Problem 10 right after, so take it through to the finish.

### Follow-up prompt

_None needed._

---

## Problem 10 — Push to GitHub and submit the URL

### Initial prompt

> **Problem 10: Push to GitHub and submit the URL (5 points)**
>
> We need to push our completed project to a public GitHub repository and submit the
> repository's URL on Canvas. The graders will clone our repository, so we must make
> absolutely sure that it is publicly accessible and that all the required files are
> present.
>
> We must include the entire `data/` folder (which contains both the course data and
> our two custom attack files) so the graders can clone the repo and run our agent
> immediately. It is critical that we do not commit our real `.env` file. We must use
> our `.gitignore` file to keep it out, and instead include an `.env.example` file that
> contains only placeholders.
>
> Having other Python files in the repository is perfectly fine. Finally, we need to add
> a short note in our `README.md` explaining exactly how to execute our agent.
>
> (The assignment also gives an expected repo layout: `AI_prompts.md`, `README.md`,
> `.gitignore`, `.env.example`, `requirements.txt`, `agent.py`, `tools.py`, `models.py`,
> `prompts/prompt.md`, the full `data/` tree including `my_attacks/`, and the `output/`
> files through `hw6_report.html`.)

### Follow-up prompt

_None needed._

---
