# Handbook size and cost estimate

**Problem 2 — Size up the handbook**
Model: `gpt-6-luna` · Measured 2026-10-18 · Script: [`count_handbook.py`](../count_handbook.py) · Raw numbers: [`handbook_tokens.json`](handbook_tokens.json)

---

## 1. Token count

**The handbook is 10,058 tokens.**

For scale, `data/shop_handbook.md` is 28,903 characters / 6,127 whitespace words / 339 lines — so roughly 2.87 characters per token, which is normal for English Markdown with tables.

### Method

I measured it two independent ways and they agree exactly.

**Method A — offline tokenizer (`tiktoken`).**
I encoded the file with `o200k_base`, the byte-pair encoding used by the GPT-4o/5/6 family, and took the length of the token list.

```python
enc = tiktoken.get_encoding("o200k_base")
tokens = len(enc.encode(handbook_text))   # -> 10058
```

I also ran the older `cl100k_base` encoding as a sanity check: 10,184 tokens, about 1.3% higher. The two being close tells me the file has no unusual content (no long base64 blobs, no CJK) that would make tokenizer choice matter much.

**Method B — ask the real API, by subtraction.**
A tokenizer tells you how the *text* encodes, but the bill is based on what the endpoint counts, which also includes per-request overhead. So I sent two calls to `gpt-6-luna` whose prompts are identical except for the handbook, and subtracted:

| Call | Input | `usage.input_tokens` |
|---|---|---|
| 1 | handbook + `"Reply with the single word: ok"` | 10,071 |
| 2 | `"Reply with the single word: ok"` alone | 13 |
| | **difference = handbook** | **10,058** |

The subtraction cancels the fixed overhead, so what is left is purely the handbook's billable size.

**Result: both methods give 10,058.** The exact match confirms `gpt-6-luna` tokenizes with `o200k_base`, which means I can use `tiktoken` offline for the rest of this assignment — no API call needed to predict a bill.

I use **10,058** for all the math below, because that is the number the endpoint actually billed.

---

## 2. Prices

From `data/prices.json`, per 1,000,000 tokens:

| Rate | $ / 1M tokens | $ / token |
|---|---|---|
| Input (uncached) | $0.10 | $0.0000001 |
| Input (cache read / hit) | $0.01 | $0.00000001 |
| Cache write | $0.125 | $0.000000125 |
| Output | $0.50 | $0.0000005 |

A cache **read** costs **10%** of a normal input token. A cache **write** costs **125%** — you pay a 25% premium once to store the prefix, then everything after is 10× cheaper.

Everything below prices **the handbook only**. The vendor document, the system instructions and the model's answer are extra; they are counted in Problem 4.

---

## 3. Cost of sending the handbook

### 3a. Without caching

Every call pays the full input rate.

**One call:**

```
10,058 tokens ÷ 1,000,000 × $0.10
  = 0.010058 × $0.10
  = $0.0010058        ≈ $0.00101   (about one tenth of a cent)
```

**1,000 calls:**

```
$0.0010058 × 1,000 = $1.0058        ≈ $1.01
```

### 3b. With caching

Caching bills the *first* call at the cache-write rate and every later call at the cache-read rate, for as long as the entry stays warm.

**Cache write (call 1):**

```
10,058 ÷ 1,000,000 × $0.125
  = 0.010058 × $0.125
  = $0.00125725       ≈ $0.00126
```

**Cache read (each later call):**

```
10,058 ÷ 1,000,000 × $0.01
  = 0.010058 × $0.01
  = $0.00010058       ≈ $0.000101
```

**1,000 calls = 1 write + 999 reads:**

```
  $0.00125725                    (call 1, write)
+ $0.00010058 × 999 = $0.10047942   (calls 2-1000, reads)
= $0.10173667                   ≈ $0.1017
```

For reference, the theoretical floor if all 1,000 calls were hits with no write to pay for is `$0.00010058 × 1,000 = $0.10058`. The real number is only $0.0012 above it, because one write spread over 1,000 calls is almost nothing.

---

## 4. Summary

| Scenario | 1 call | 1,000 calls |
|---|---|---|
| No caching | $0.0010058 | **$1.0058** |
| Caching (1 write + 999 reads) | $0.0012573 (write) / $0.0001006 (read) | **$0.1017** |
| **Savings** | — | **$0.9041 (89.9% cheaper)** |

### What this means

- Caching cuts the handbook's cost by **about 10×**. The saving is capped at 90% because a cache read is 10% of an input token — that is the floor, you cannot do better than that by caching alone.
- The one-time write premium is real but trivial at volume. Caching is already cheaper than not caching from **call 2 onward**: after two calls you have paid $0.0013583 cached versus $0.0020116 uncached.
- Caching only pays off if the handbook sits at the **front** of the prompt and is **byte-identical** every time. Prefix caching matches from the first token forward, so putting even a timestamp or the vendor document before the handbook would break every hit and silently push the bill back toward $1.01 per 1,000 calls.
- For this assignment's 22 documents the absolute numbers are small (22 calls ≈ $0.022 uncached). The point is the rate: a vendor desk processing 1,000 documents a day would spend **$367/year** on the handbook alone uncached versus **$37/year** cached.

**To be verified in Problem 4:** that real runs report `cached_tokens ≈ 10,058` on calls 2+, and that measured spend tracks the $0.1017-per-1,000 line rather than the $1.0058 one.
