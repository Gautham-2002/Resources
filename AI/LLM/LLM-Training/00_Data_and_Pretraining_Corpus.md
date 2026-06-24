# 00 — Data: The Pre-Training Corpus
### What Gets Fed Into an LLM and How It Gets Cleaned

> **Key insight:** An LLM's "knowledge" is a compressed statistical summary of its training data. The quality, diversity, and scale of that data — not just the architecture — determines what the model can and cannot do.

---

## Part 1 — Scale: How Much Text Does a Modern LLM Need?

Training a frontier LLM requires trillions of tokens. To put this in perspective:

```
1 token ≈ 0.75 words (rough average for English text)

GPT-3 (2020):       300 Billion tokens    ≈ 225B words
LLaMA 1 (2023):     1.4 Trillion tokens   ≈ 1.05T words
LLaMA 2 (2023):     2.0 Trillion tokens
LLaMA 3 (2024):     15.6 Trillion tokens
Chinchilla (2022):  1.4 Trillion tokens   (70B model)

For comparison:
  - The entire English Wikipedia: ~4.4B words ≈ 5.9B tokens
  - A prolific human reader reads ~3M words/year
  - LLaMA 3 was trained on the equivalent of 14 million prolific human readers' lifetime of text
```

This isn't academic reading. It's the raw, noisy, multilingual internet — and making it usable requires extensive engineering.

---

## Part 2 — Where Does the Data Come From?

### 2.1 Common Crawl — The Backbone

[Common Crawl](https://commoncrawl.org/) is an open repository of web crawl data that has been continuously archiving the internet since 2008. It is the primary data source for virtually every major LLM.

```
Common Crawl statistics (2024):
  - ~3.15 billion web pages indexed
  - ~250TB of raw HTML/WARC data per monthly crawl
  - ~20 years of archived crawls available
  - Used by: GPT-3, PaLM, LLaMA, Mistral, Falcon, Gemma...
```

**Raw Common Crawl is nearly unusable.** It contains:
- Spam, SEO garbage, and boilerplate templates
- Duplicate content at massive scale
- Adult content, hate speech, personal data
- Non-natural language (JavaScript, HTML, CSS, SQL dumps)
- Machine-translated low-quality text

The challenge is filtering this down to high-quality natural language.

### 2.2 Curated Web Datasets Derived from Common Crawl

| Dataset | Description | Size |
|---------|-------------|------|
| **C4** (Raffel et al., 2019) | Common Crawl + quality filters. Used for T5. | ~750GB |
| **The Pile** (EleutherAI, 2021) | 22 diverse sources including books, GitHub, arXiv, PubMed | 825GB |
| **RefinedWeb** (Falcon, 2023) | Aggressive dedup + quality filters on Common Crawl | 5TB |
| **DCLM** (2024) | Model-based quality filtering on Common Crawl | 3.8T tokens |

### 2.3 Other Key Data Sources

```
Books:
  ├── Books3 / BookCorpus     (novels, non-fiction)
  ├── Project Gutenberg       (public domain books)
  └── OpenLibrary             (book previews)

Code:
  ├── GitHub (The Stack, StarCoder datasets)
  ├── StackOverflow posts
  └── Software documentation

Academic:
  ├── arXiv papers (math, physics, CS, biology)
  ├── PubMed Central (biomedical literature)
  └── SemanticScholar corpus

Reference:
  ├── Wikipedia (all languages)
  └── Wikidata

Conversational:
  ├── Reddit (pushshift.io dumps)
  └── StackExchange Q&A
```

**Why include code?** Code-trained models show better reasoning ability even on non-code tasks. The structured, logical nature of code seems to improve general reasoning. LLaMA 3's 15T token corpus was reportedly ~8% code.

---

## Part 3 — Data Quality Pipeline

Raw web data goes through a multi-stage quality pipeline. This is where the real engineering happens.

```
Raw Common Crawl HTML
         │
         ▼ [Step 1: Text Extraction]
Plain text (UTF-8)
         │
         ▼ [Step 2: Language Identification]
English (and target languages)
         │
         ▼ [Step 3: Heuristic Quality Filters]
Filtered text
         │
         ▼ [Step 4: Deduplication]
Deduplicated text
         │
         ▼ [Step 5: Model-Based Quality Scoring]
High-quality text
         │
         ▼ [Step 6: Mixing and Sampling]
Final training corpus
```

### Step 1 — Text Extraction

Convert raw HTML to clean plain text:
- Strip HTML tags, JavaScript, CSS, navigation menus
- Decode Unicode properly (handle encoding errors)
- Segment into natural paragraphs

Tool: `trafilatura`, `jusText`, or custom parsers. This alone removes ~60-70% of bytes.

### Step 2 — Language Identification

Use a fast language classifier (e.g., `fastText` `lid.176.bin` model) to keep only target languages.

For English-centric models, non-English text is either filtered or kept at a controlled proportion for multilingual capability.

### Step 3 — Heuristic Quality Filters

A battery of rule-based filters, tuned empirically:

```
KEEP if:
  ✓ Text length > 100 words (removes stub pages)
  ✓ Mean word length ∈ [3, 10] characters (filters gibberish)
  ✓ Fraction of alphabetic characters > 0.8 (filters number-heavy spam)
  ✓ Fraction of stop words > threshold (natural language indicator)
  ✓ Fraction of lines ending in punctuation > 0.6 (prose-like structure)
  ✓ No more than N deduplicated lines (template filter)

REMOVE if:
  ✗ Contains > 3 curse words (noisy content)
  ✗ Contains common spam phrases ("click here", "buy now" density)
  ✗ Character-level entropy too low (repetitive) or too high (garbled)
  ✗ Fraction of lines starting with bullet/special char too high
  ✗ Known adult content domain list
```

These filters vary by lab. Meta's RedPajama and Mistral's data pipelines are more aggressive than early GPT-3 pipelines.

### Step 4 — Deduplication: The Most Impactful Step

**Deduplication is arguably the most important data quality step.** The web has massive amounts of duplicate content:
- Scraped articles republished on hundreds of sites
- Legal boilerplate, cookie consent text, headers/footers
- Mirror sites and content farms

Without deduplication, the model sees the same text thousands of times, leading to:
1. **Memorization** — the model can recite verbatim passages (copyright/privacy risk)
2. **Distributional shift** — common boilerplate dominates rare but informative text

**Types of deduplication:**

```
1. Exact Match Deduplication
   └── Hash (SHA256) each document; remove exact duplicates.
   └── Fast, but misses near-duplicates.

2. Near-Duplicate Deduplication (MinHash + LSH)
   ├── MinHash: For each document, compute a "fingerprint" from K min-hashes
   │            of its N-gram shingles.
   ├── LSH (Locality Sensitive Hashing): Group similar fingerprints into buckets.
   └── Documents in the same bucket are near-duplicates; keep one.

   Threshold: Jaccard similarity > 0.8 → considered duplicate.

3. Substring-Level Deduplication
   └── Suffix array approach (Lee et al., 2022): Find repeated substrings
       across documents, not just at document level.
   └── Effective for catching template boilerplate embedded in otherwise
       unique documents.
```

**Scale of deduplication impact:**

```
C4 corpus:    174B tokens raw → 750GB after dedup (significant reduction)
The Pile:     ~825GB after aggressive dedup from many TB of raw data
LLaMA 1:      The team found that deduplication improved benchmark
              performance more than equivalent increases in model size.
```

### Step 5 — Model-Based Quality Scoring

Pure heuristics miss a lot. Modern pipelines use a trained classifier to score document quality.

**Two approaches:**

**A. Classifier trained on Wikipedia/Books vs. Common Crawl**

Train a binary classifier:
- Positive examples: Wikipedia articles, published books (high-quality)
- Negative examples: random Common Crawl documents

Score each web document; keep documents with high "Wikipedia-like" quality score.

Used in GPT-3's data pipeline.

**B. Perplexity Filter (CCNet approach, Wenzek et al., 2019)**

Train a small language model (5-gram KenLM) on a high-quality reference corpus (Wikipedia).  
Compute the perplexity of each document under this model.  
**Keep low-perplexity documents** (the model can predict them well → they resemble high-quality text).

```
Document perplexity under Wikipedia-trained KenLM:

Low PPL   → Looks like Wikipedia → HIGH QUALITY → KEEP
High PPL  → Gibberish, non-English, spam → DISCARD
```

**C. DCLM's Model-Based Approach (2024)**

Train a small classifier LM, score all candidate documents, keep top percentiles.  
The DCLM paper showed this produces significantly better downstream models than heuristic-only filtering.

### Step 6 — Mixing and Sampling

Not all sources are created equal. The final corpus is constructed by **sampling from each source at a controlled rate**:

```
Example data mixture (approximate, based on public reports):

Source                    Weight    Reasoning
────────────────────────────────────────────────────────
Common Crawl (filtered)    ~70%     Volume
GitHub (code)               ~8%     Reasoning capability
Wikipedia (all languages)   ~4%     Factual grounding
Books                       ~6%     Long-form coherence
arXiv                       ~2%     Technical reasoning
StackExchange               ~2%     Q&A format
Other                       ~8%     Diversity
```

**Why not just use all Common Crawl?** Diversity matters. A model trained only on web text is worse at structured reasoning (code, math) than a model with targeted high-quality sources in the mix.

**Why not more Wikipedia?** Wikipedia represents a tiny fraction of total data but is highly polished. Over-representing it causes the model to "talk like Wikipedia" — formal, hedged, not conversational.

---

## Part 4 — Tokenization at Scale

After cleaning, text is converted to tokens using a **Byte Pair Encoding (BPE)** tokenizer trained on a sample of the final corpus.

The tokenizer vocabulary is **trained before the model** — it's a data preprocessing artifact, not a model weight.

### BPE Training at Scale

```
Start: every byte (256 possible values) is a token

Repeat until vocab_size is reached:
  1. Count all adjacent token pairs in the corpus
  2. Find the most frequent pair (e.g., "t" + "h" → "th")
  3. Merge that pair into a new token
  4. Update the corpus to use the new merged token
  5. Continue

Result: a vocabulary of ~32K–100K tokens covering all frequent substrings
```

For LLaMA 3: vocabulary of 128,000 tokens (vs. GPT-2's 50,257).  
Larger vocabularies → fewer tokens per document → faster training throughput.

### Tokenization is Irreversible

Once the corpus is tokenized and written to disk in binary format, the text is gone. What remains is a massive binary file of integer token IDs:

```
Typical storage format for training:
  - uint16 or uint32 per token (2-4 bytes)
  - 1 trillion tokens × 2 bytes = 2TB of binary data
  - Written in sharded files for distributed reading

LLaMA 3 training corpus: 15.6T tokens
  → 15.6T × 2 bytes = ~31TB of tokenized binary data
```

---

## Part 5 — Data Ethics and Contamination

### Benchmark Contamination

If the training data contains the test sets of evaluation benchmarks (HellaSwag, MMLU, etc.), benchmark scores are inflated. This is a significant problem because Common Crawl contains essentially everything on the public internet.

Modern labs attempt to detect and remove known benchmarks from training data, but this is imperfect.

### Privacy and Copyright

- Web crawls contain personal information (emails, phone numbers, addresses)
- Models can memorize training data, especially duplicated sequences
- Copyright status of internet-scraped content is legally contested (multiple active lawsuits as of 2024)

**Mitigations:**
- Deduplication reduces verbatim memorization risk
- PII detection and removal filters for email addresses, phone numbers, SSNs
- Some labs exclude known copyrighted sources (e.g., certain book publishers' catalogs)

---

## Part 6 — The Data Quality Flywheel

```
Better data filters
        │
        ▼
Better pre-trained model
        │
        ▼
Better model-based quality classifier
        │
        ▼
Better data filters (iterate)
```

This is why lab data pipelines are proprietary — the quality of the pre-trained base model is a direct function of the quality of the data pipeline, and this compounds over training runs.

---

## Summary

| Step | What Happens | Impact |
|------|-------------|--------|
| Crawl | Collect raw HTML from the internet | Volume |
| Extract | Strip HTML, get plain text | Noise reduction |
| Language filter | Keep target language(s) | Precision |
| Heuristic filter | Length, stop words, line endings | Quality gate |
| Deduplication | Remove near-duplicate documents | Biggest quality lift |
| Quality scoring | Model-based classifier or KenLM PPL filter | Further quality lift |
| Mixing | Blend sources at controlled ratios | Diversity |
| Tokenization | BPE → binary token IDs | Training efficiency |

The pre-training corpus is not "the internet." It is a carefully curated, massively deduplicated, quality-filtered slice of the internet — assembled through months of engineering effort before a single GPU is turned on for training.

---

*Next: [01 — Pre-Training: Learning from the World](./01_Pretraining.md)*
