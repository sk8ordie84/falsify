.PHONY: help install test smoke ci demo doctor clean lint-skills version

help:
	@echo "Falsification Engine — common targets"
	@echo "  make install      — install dependencies (pyyaml)"
	@echo "  make test         — run unittest suite"
	@echo "  make smoke        — run smoke_test.sh"
	@echo "  make ci           — run the same checks as GitHub Actions"
	@echo "  make demo         — run the JUJU end-to-end demo"
	@echo "  make doctor       — run falsify doctor"
	@echo "  make lint-skills  — validate skill/agent frontmatter"
	@echo "  make version      — print current falsify version"
	@echo "  make clean        — remove generated .falsify/ runs (keep specs)"

install:
	pip install pyyaml

test:
	python3 -m unittest discover tests -v

smoke:
	bash tests/smoke_test.sh

ci: test smoke demo lint-skills

demo:
	python3 falsify.py lock juju
	python3 falsify.py run juju
	python3 falsify.py verdict juju

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
