# Convenience forwarder: the real Makefile is at the repository root.
#
# Backend work happens in this directory, so `make test` gets typed here by
# reflex. Rather than fail with "No rule to make target", delegate upward.
# Nothing is defined twice - every recipe lives in ../Makefile.

.PHONY: dev test lint check

dev test lint check:
	@$(MAKE) -C .. $@
