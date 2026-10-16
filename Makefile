# One-command runner (wired up in a later stage).
# Stage 0: this only prints a reminder.

.PHONY: help run

help:
	@echo "AI Tech Consultant"
	@echo "  make run   — start all three services (not implemented yet)"

run:
	@echo "Stage 0 only: folders and git are set up."
	@echo "Later stages will start Task 1, then Task 2, then Task 3."
