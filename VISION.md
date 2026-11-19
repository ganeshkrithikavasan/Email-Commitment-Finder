# Vision

## Email Harness

A small scale AI system that reads email and figures out two things:

1. **Does this email contain a commitment or a deadline?** If so, what is it, who made it, and how sure are we?
2. **Who and what is this email actually about?** Emails mention the same client, deal, or project in a dozen inconsistent ways. The goal of this project is to link those mentions together into one clear picture.

I am using a well known public dataset (Enron) and not someone's private inbox.

## Personal goal for building this project

I've spent 15 years in R&D and product management, and the last several years focused on AI products in the legal tech space. Before writing any code, here is a question I would ask about a feature like this if someone else had built it: when does it actually save a person time, and when does it become one more thing they have to double check?

A few more questions to ask if I were scoping this as a product rather than building it myself:

- **How often is the system confident, and how often does it have to say "I'm not sure"?** A system that is only usable a fifth of the time doesn't save anyone work; it just adds a new task on top of the old one.
- **Which mistake costs more: missing a real deadline, or flagging something that isn't one?** These have very different costs depending on the workflow, and it is easy to tune for the wrong one by default.
- **What does it cost per email to run, on different models? Does that number still make sense at the volume a real product would actually see?** I'm answering this one with a real side-by-side: the same extraction task run on a frontier model (Claude Sonnet) and on a small, free, locally-run model (DeepSeek-R1, 14B, via Ollama on my own machine). Not to prove the free model is secretly just as good, but to see exactly what it costs in quality to get that cost down to near zero, and where that trade stops being worth it.
- **Does "I'm not sure" make people start ignoring the system entirely after catching it wrong once?**
- **Can the system explain why it decided what it decided?** In a legal or compliance adjacent workflow, this is not optional.

Those are the questions I would ask as an AI PM. This project answers them myself, with a real system and real numbers.

## How I'm building it

The core idea is simple: **don't trust a single prediction from an AI model. Check it, and know when to say "I'm not sure."**

Every email goes through a small pipeline:

1. **Extract** - an AI model reads the email and pulls out whatever commitments or deadlines it finds. It will then assign a confidence score for each one.
2. **Check** - a second independent pass reviews that extraction. Part of this check is another AI model; part of it is plain old-fashioned code, like does this date actually exist, or is the confidence score even in a valid range. Mixing an AI check with a hard-coded check catches different kinds of mistakes.
3. **Decide** - if the extraction is solid and both checks agree, then accept it. If not, then try again once, now knowing the difference or disagreement. If it is still unclear, then mark it as "unsure" and flag it for a person to look at, rather than guessing and hoping. This is the "human in the loop" part.
4. **Record / Audit** - every single decision is logged. What the input was, what came out, how confident the system was, which exact version of the prompt and model were used, and what it cost in time and tokens.

That loop of extract, check, decide, record is our project's "harness." It is the scaffolding of ordinary code that sits around an AI model to make it repeatable and accountable.

I'm building it in stages, and each stage has to work before I move on:

1. **Get the core loop working** on real email - extract, check, decide, record.
2. **Add memory for people and companies** - using embeddings (a way of turning text into numbers that capture meaning) so the system can recognize that "Acme Corp," "Acme," and "the Acme deal" are all the same thing, even across different emails.
3. **Turn it into tools an AI agent can call** - wired up over MCP (a standard way for AI systems to use tools), instead of one big hardcoded script.
4. **Test it properly** - a real evaluation set of cases, checking accuracy, how often it makes things up, how fast it is, and what it costs to run. This is also where the Sonnet-vs-DeepSeek-R1 tokenomics comparison lives: same pipeline, same prompts, one frontier model and one free local model, run side by side so the cost and quality tradeoff gets measured, not guessed.
5. **Write it up** - a plain account of what was built, what worked, what didn't, and what I'd do differently at scale.
