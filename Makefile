ifeq ($(OS),Windows_NT)
PLATFORM_MAKEFILE := Makefile.win
else
PLATFORM_MAKEFILE := Makefile.linux
endif

.DEFAULT_GOAL := help

.PHONY: help
help:
	@$(MAKE) --no-print-directory -f $(PLATFORM_MAKEFILE) help

%:
	@$(MAKE) --no-print-directory -f $(PLATFORM_MAKEFILE) $@
