# Security Policy

This project is a design pattern and a dependency-free reference implementation.
It has no runtime, no network access, and no third-party dependencies — so its
attack surface is small. Still, if you find a problem, we want to hear about it.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Instead, email
**nskit@nskit.io** with:

- a description of the issue and why you think it's a security concern,
- steps to reproduce (a minimal fixture project is ideal), and
- the commit or version you observed it on.

We aim to acknowledge reports within a few business days.

## Scope

In scope:

- a contract that can be made to report a **false negative** (misses a real
  violation) or a **false positive** (fires on a look-alike) in a way that
  undermines trust in the gate — for example, a comment or template construct
  that defeats `blank_comments`;
- a crafted source tree that makes the scanner crash, hang, or read outside the
  project root.

Out of scope:

- the correctness of any individual contract's *policy* (whether a rule is a good
  idea) — open a normal issue or PR for that;
- anything in the example fixtures under `examples/`, which contain deliberately
  "broken" code to demonstrate failures.
