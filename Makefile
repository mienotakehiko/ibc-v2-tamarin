# ivc-v2-tamarin --- convenience Makefile for measure_rev6.py
#
# Override any variable on the command line, e.g.
#   make proofs TAMARIN=/opt/tamarin-1.12.0/bin/tamarin-prover RUNS=3

TAMARIN  ?= tamarin-prover
RUNS     ?= 3
THREADS  ?= 1
HEAP_GB  ?= 8
TIMEOUT  ?= 7200

THEORY_DIR := theories
TRANSPORT  := $(THEORY_DIR)/ibcv2_transport_nat.spthy
P4DIAG     := $(THEORY_DIR)/ibcv2_p4_nat_diagnostic.spthy
ICS20      := $(THEORY_DIR)/ibcv2_ics20_projection.spthy

MEASURE := ./measure_rev6.py \
	--runs $(RUNS) \
	--threads $(THREADS) \
	--heap-gb $(HEAP_GB) \
	--tamarin $(TAMARIN)

.PHONY: check smoke transport-sanity p4 p4diag p6pilot p6sanity proofs clean help

help:
	@echo 'Available targets:'
	@echo '  check              parse-only pass over the three theory files'
	@echo '  smoke              run the seven transport lemmas once'
	@echo '  transport-sanity   run the three transport executability lemmas'
	@echo '  p4                 run P4 and its two helpers (RUNS, TIMEOUT respected)'
	@echo '  p4diag             run the P4 helper-hidden diagnostic (600 s cap)'
	@echo '  p6pilot            run the four P6 safety lemmas once'
	@echo '  p6sanity           run the two P6 executability lemmas once'
	@echo '  proofs             the full paper batch (11 lemmas x RUNS runs)'
	@echo '  clean              delete every subdirectory of results/'
	@echo
	@echo 'Overridable variables: TAMARIN, RUNS, THREADS, HEAP_GB, TIMEOUT'

check:
	$(TAMARIN) --parse-only $(TRANSPORT) +RTS -N1 -M$(HEAP_GB)G -RTS
	$(TAMARIN) --parse-only $(P4DIAG)    +RTS -N1 -M$(HEAP_GB)G -RTS
	$(TAMARIN) --parse-only $(ICS20)     +RTS -N1 -M$(HEAP_GB)G -RTS

smoke:
	$(MEASURE) --suite smoke-transport --runs 1 --timeout 1800

transport-sanity:
	$(MEASURE) --suite sanity-transport --runs 1 --timeout 1800

p4:
	$(MEASURE) --suite p4 --timeout $(TIMEOUT)

p4diag:
	$(MEASURE) --suite p4diag --runs 1 --timeout 600

p6pilot:
	$(MEASURE) --suite smoke-p6 --runs 1 --timeout 1800

p6sanity:
	$(MEASURE) --suite sanity-p6 --runs 1 --timeout 1800

proofs:
	$(MEASURE) --suite proofs --timeout $(TIMEOUT)

clean:
	rm -rf results/*
