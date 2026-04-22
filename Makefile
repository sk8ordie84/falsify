.PHONY: help install test smoke ci demo demo-script doctor clean lint-skills version docker-build docker-run dogfood self-status release-check

help:
	@echo "Falsification Engine — common targets"
	@echo "  make install      — install dependencies (pyyaml)"
	@echo "  make test         — run unittest suite"
	@echo "  make smoke        — run smoke_test.sh"
	@echo "  make ci           — run the same checks as GitHub Actions"
	@echo "  make demo         — run the JUJU end-to-end demo"
	@echo "  make demo-script  — run the auto-narrated ./demo.sh walkthrough"
	@echo "  make doctor       — run falsify doctor"
	@echo "  make lint-skills  — validate skill/agent frontmatter"
	@echo "  make version      — print current falsify version"
	@echo "  make clean        — remove generated .falsify/ runs (keep specs)"
	@echo "  make docker-build — build the falsify-demo Docker image"
	@echo "  make docker-run   — run the auto-demo in a container"
	@echo "  make dogfood      — re-run the three self-claims (cli_startup, test_coverage_count, claude_surface)"
	@echo "  make self-status  — print `falsify why` for each self-claim"
	@echo "  make release-check — 12-gate pre-release validator (run before tagging)"

install:
	pip install pyyaml

test:
	python3 -m unittest discover tests -v

smoke:
	bash tests/smoke_test.sh

ci: test smoke demo lint-skills dogfood

demo:
	python3 falsify.py lock juju
	python3 falsify.py run juju
	python3 falsify.py verdict juju

demo-script:
	./demo.sh

doctor:
	python3 falsify.py doctor

lint-skills:
	@python3 -c "import yaml, glob, sys; \
	fails = []; \
	paths = glob.glob('.claude/skills/*/SKILL.md') + glob.glob('.claude/agents/*.md'); \
	[fails.append(p) for p in paths if not yaml.safe_load(open(p).read().split('---')[1]) or 'name' not in yaml.safe_load(open(p).read().split('---')[1])]; \
	print('OK' if not fails else 'FAIL: ' + ','.join(fails)); \
	sys.exit(1 if fails else 0)"

version:
	@python3 falsify.py --version

clean:
	@find .falsify -type d -name 'runs' -exec rm -rf {} + 2>/dev/null || true
	@find .falsify -name 'verdict.json' -delete 2>/dev/null || true
	@echo "Cleaned .falsify/*/runs and verdict.json (specs preserved)"

docker-build:
	docker build -t falsify-demo .

docker-run:
	docker run --rm -it falsify-demo

dogfood:
	@for claim in cli_startup test_coverage_count claude_surface; do \
		python3 falsify.py run $$claim || exit 1; \
		python3 falsify.py verdict $$claim || exit 1; \
	done
	@python3 falsify.py score --format text

self-status:
	@for claim in cli_startup test_coverage_count claude_surface; do \
		python3 falsify.py why $$claim; \
		echo ""; \
	done

release-check:
	python3 scripts/release_check.py --all
