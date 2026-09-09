# ibc-v2-tamarin

A Tamarin Prover artifact for the formal security verification of **Cosmos IBC v2**.

This repository is the companion artifact to the paper
*Formal Security Verification of IBC v2 Using the Tamarin Prover*
(single author, T. Mieno). It contains everything a third party needs to
reproduce the paper's measured results: three Tamarin theories, a
measurement harness, a `Makefile` that drives the harness, and the exact
log batch that produced the numbers reported in the paper.

The intent of this repository is narrow. It is not a general-purpose IBC
model; it is the minimum executable evidence that the six security
properties enumerated in the paper mechanically verify under the stated
threat model.

## Scope of the artifact

The verification covers six protocol-level properties of IBC v2, split
across three theories:

| Property | Statement | Theory |
|---|---|---|
| **P1** Authentic Delivery | Every `recvPacket` on chain *B* is preceded by a matching `sendPacket` on chain *A*. | `ibcv2_transport_nat.spthy` |
| **P2** Exactly-once Receipt | No two distinct `recvPacket` actions succeed for the same `(destClientId, sequence)`. | `ibcv2_transport_nat.spthy` |
| **P3** ACK Correspondence | Every successful `acknowledgePacket` on *A* is preceded by a matching `recvPacket` on *B*. | `ibcv2_transport_nat.spthy` |
| **P4** Timeout Safety | `timeoutPacket` succeeds only if no `recvPacket` for that packet has succeeded. | `ibcv2_transport_nat.spthy` (helper), `ibcv2_p4_nat_diagnostic.spthy` (helper-hidden comparison) |
| **P5** Client or Port Binding | An adversarial relayer cannot rewire a packet to a different client, port, sequence, timeout, or payload. | `ibcv2_transport_nat.spthy` |
| **P6** Transfer-local Fund Conservation (ICS-20) | For a single ICS-20 transfer: mint and refund each imply a prior lock; at most one mint occurs; mint and refund are mutually exclusive. | `ibcv2_ics20_projection.spthy` |

The threat model is a Dolev-Yao network attacker in control of every
relayer, with light-client verification treated as an axiomatised
predicate (`VerifyMembership`, `VerifyNonMembership`). Full details of
the modelling choices live in the paper; the theory files are heavily
commented so they can be read on their own.

## Repository layout

```
.
├── README.md                          ← this file
├── LICENSE                            ← MIT license
├── CITATION.cff                       ← citation metadata for GitHub
├── Makefile                           ← convenience targets for `measure_rev6.py`
├── measure_rev6.py                    ← measurement harness (Python 3.10+)
├── SHA256SUMS                         ← SHA-256 digests of the tracked source files
├── theories/
│   ├── ibcv2_transport_nat.spthy       (246 lines, P1-P5 and height helpers)
│   ├── ibcv2_p4_nat_diagnostic.spthy   (165 lines, P4 helper vs. no-helper)
│   └── ibcv2_ics20_projection.spthy    (131 lines, P6a-P6d transfer-local)
└── results/
    └── 20260831-184158-proofs-N1/     ← the published measurement batch
        ├── environment.txt
        ├── runs.csv
        ├── summary.csv
        ├── summary.md
        └── *.log / *.time             ← 33 per-run logs, one per (lemma, run)
```

Everything outside this list is deliberately absent. The paper source
lives in a separate repository, so this artifact stays focused on the
executable proof material.

## Requirements

The measurements in the paper were produced on the following stack:

| Component | Version used |
|---|---|
| Tamarin Prover | 1.12.0 (git `82780bba`) |
| Maude | 3.5.1 |
| Python | 3.14.6 |
| GNU `time` (`/usr/bin/time`) | any recent GNU coreutils |
| Operating system | WSL2 on Linux 5.15 (x86_64) |
| Host memory | 50 GiB RAM, 12 GiB swap |

Tamarin 1.12.0 is a strict lower bound: earlier releases lack the
`natural-numbers` builtin that the theories depend on. Any Linux or
macOS host with at least 8 GiB of usable RAM should suffice; the heaviest
observed working-set was under 500 MiB.

Install Tamarin per the upstream instructions
(<https://tamarin-prover.com/manual/master/book/002_installation.html>).
`maude` and `/usr/bin/time` are usually available through the system
package manager. The measurement harness is a single-file Python script
with no third-party dependencies.

## Quick start

Clone the repository and confirm that every theory parses cleanly:

```bash
git clone https://github.com/mienotakehiko/ibc-v2-tamarin.git
cd ibc-v2-tamarin
make check TAMARIN=$(which tamarin-prover)
```

Once `make check` succeeds, a one-shot smoke test verifies the transport
theory:

```bash
make smoke TAMARIN=$(which tamarin-prover)
```

The smoke suite runs the seven transport lemmas (P1-P5 plus two height
helpers) once each and prints a Markdown summary. Expect a total wall
time of roughly one minute on a modern laptop; peak resident memory
stays below 500 MiB.

## Reproducing the paper's measurements

The full measurement batch reported in the paper consists of eleven
safety lemmas run three times each (thirty-three runs total), under a
fixed single-threaded configuration with an 8 GiB heap cap and a
7200-second wall-clock timeout per run:

```bash
make proofs \
    TAMARIN=$(which tamarin-prover) \
    RUNS=3 \
    THREADS=1 \
    HEAP_GB=8 \
    TIMEOUT=7200
```

Each invocation of `make proofs` creates a fresh timestamped directory
under `results/`, for example `results/20260901-084215-proofs-N1/`. The
directory contains:

- `environment.txt` — a fingerprint of the host, including Tamarin and
  Maude versions and a SHA-256 digest of every tracked file at run time;
- `runs.csv` — one row per individual run, with wall time, maximum RSS,
  exit code, and Tamarin's reported outcome;
- `summary.csv` and `summary.md` — the per-lemma median across the three
  runs, in machine- and human-readable form;
- `*.log` — the full Tamarin stdout/stderr for each run;
- `*.time` — the `/usr/bin/time -f "maxrss_kb=%M"` output for each run.

Wall time is captured with Python's `time.perf_counter()`; maximum
resident set size is captured with GNU `time`. Executability lemmas
(`Executable*`) are automatically launched with `--stop-on-trace=BFS`,
because the unbounded `Tick` rule leads the default depth-first search
into an irrelevant branch.

The batch archived under
`results/20260831-184158-proofs-N1/` is the exact set of logs behind the
numbers in Table 3 of the paper. Any reproduction that stays within the
same major versions of Tamarin and Maude should match those numbers to
within noise.

## Expected outcomes

Every safety lemma verifies within a few seconds; the heaviest lemma is
P2 at roughly thirty-five seconds. The published batch produced the
following medians across three runs each:

| Theory | Lemma | Outcome | Median steps | Median wall (s) | Median Max RSS (KiB) |
|---|---|---|---:|---:|---:|
| `ibcv2_transport_nat.spthy` | `P1_AuthenticDelivery` | verified | 8 | 3.18 | 110,788 |
| `ibcv2_transport_nat.spthy` | `P2_ExactlyOnceReceipt` | verified | 544 | 34.67 | 467,760 |
| `ibcv2_transport_nat.spthy` | `P3_AckCorrespondence` | verified | 5 | 3.38 | 108,376 |
| `ibcv2_transport_nat.spthy` | `ReceiptBeforeHeight` | verified | 3 | 2.42 | 39,996 |
| `ibcv2_transport_nat.spthy` | `WitnessBeforeReceiptHeight` | verified | 3 | 2.27 | 39,928 |
| `ibcv2_transport_nat.spthy` | `P4_TimeoutSafety` | verified | 25 | 3.73 | 103,228 |
| `ibcv2_transport_nat.spthy` | `P5_ClientPortBinding` | verified | 2 | 2.42 | 41,572 |
| `ibcv2_ics20_projection.spthy` | `P6_MintImpliesLock` | verified | 4 | 3.68 | 58,744 |
| `ibcv2_ics20_projection.spthy` | `P6_RefundImpliesLock` | verified | 4 | 3.73 | 56,940 |
| `ibcv2_ics20_projection.spthy` | `P6_NoDoubleMint` | verified | 16 | 3.98 | 59,464 |
| `ibcv2_ics20_projection.spthy` | `P6_NoMintAndRefund` | verified | 7 | 3.78 | 61,252 |

No lemma times out, no counterexample surfaces, and no run exceeds the
8 GiB heap cap.

## Available `make` targets

The `Makefile` is a thin wrapper around `measure_rev6.py`. All targets
accept `TAMARIN`, `RUNS`, `THREADS`, `HEAP_GB`, and `TIMEOUT` as
override variables.

| Target | What it does |
|---|---|
| `make check` | Parse-only pass over the three theory files. |
| `make smoke` | Run the transport suite once (P1-P5 plus height helpers). |
| `make transport-sanity` | Run the three transport executability lemmas once. |
| `make p4` | Run P4 and its two helpers with the default `RUNS` and `TIMEOUT`. |
| `make p4diag` | Run the P4 helper-hidden diagnostic (600 s cap, single run). |
| `make p6pilot` | Run the four P6 safety lemmas once. |
| `make p6sanity` | Run the two P6 executability lemmas once. |
| `make proofs` | The full paper batch: eleven safety lemmas, three runs each. |
| `make clean` | Delete every subdirectory of `results/`. |

Invoking `measure_rev6.py` directly is also supported for finer control;
see the top of the script for the exact suite definitions.

## Integrity check

Every tracked source file has a SHA-256 digest recorded in
`SHA256SUMS`. To verify that a checkout matches the published artifact:

```bash
sha256sum -c SHA256SUMS
```

The measurement harness additionally writes a fresh SHA-256 digest of
every theory file into `environment.txt` at the start of each run, so
the identity of the sources measured in any particular batch is always
recoverable from the batch directory itself.

## How to read the theories

Each theory file is self-contained and lightly commented; a reader
familiar with Tamarin syntax should be able to follow the model without
external reference.

- `ibcv2_transport_nat.spthy` encodes the four packet-lifecycle rules
  (`SendPacket`, `RecvPacket`, `AckPacket`, `TimeoutPacket`) using a
  linear `RecvOpen` token to derive exactly-once receipt from
  Tamarin's linear-fact semantics rather than from an explicit
  restriction. Destination block time uses the `natural-numbers`
  builtin. Two `[use_induction, reuse]` height invariants are proved by
  induction and drive the P4 proof.
- `ibcv2_p4_nat_diagnostic.spthy` mirrors the transport rules and
  attaches two P4 lemmas: one with the height helpers exposed and one
  with them hidden by `hide_lemma`. Comparing the two runs empirically
  confirms that the helpers are proof-search accelerators and not
  additional protocol assumptions.
- `ibcv2_ics20_projection.spthy` is a single-transfer projection for
  ICS-20 built on a linear `PacketOpen` interface token. The refund
  branch outputs a terminal `RefundedFunds(A,u,v)` fact rather than
  routing back to `Funds(A,u,v)`, which keeps the projection strictly
  single-transfer and eliminates a re-entry cycle that previously made
  `P6_NoMintAndRefund` time out.

## Limitations

This artifact makes no claim beyond what is verified. In particular:

- Light-client soundness is axiomatised, not proved.
- Packets are single-payload; multi-payload packets are future work.
- P6 is transfer-local; a global token-supply conservation theorem is
  not proved.
- Destination height is a discrete natural-number counter; quantifying
  the safe lag of a real finality gadget is out of scope.
- The application callbacks are treated as opaque; correctness of a
  specific application module is orthogonal to the transport-level
  claims made here.

## License

The source in this repository is released under the MIT License; see
`LICENSE` for the full text.

## Contact

For questions, bug reports, or suggestions about the model itself,
please open an issue on
<https://github.com/mienotakehiko/ibc-v2-tamarin>. Correspondence
regarding the paper may be directed to
`mieno.takehiko2@exc.epson.co.jp`.
