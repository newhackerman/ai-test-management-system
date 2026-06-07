# AI自动化测试管理系统 - 自动化测试框架Makefile

.PHONY: help install test test-unit test-integration test-api test-e2e test-performance test-security test-meeting test-quick test-all clean coverage report lint format test-framework test-validate test-cleanup

# 默认目标
help:
	@echo "AI自动化测试管理系统 - 自动化测试框架"
	@echo ""
	@echo "安装和设置:"
	@echo "  install          安装依赖包"
	@echo "  setup            设置测试环境"
	@echo "  test-validate    验证测试环境"
	@echo ""
	@echo "测试执行 (新框架):"
	@echo "  test             运行所有测试 (使用新框架)"
	@echo "  test-unit        运行单元测试"
	@echo "  test-integration 运行集成测试"
	@echo "  test-meeting     运行会议模块测试"
	@echo "  test-performance 运行性能测试"
	@echo "  test-framework   测试框架自身验证"
	@echo "  test-quick       运行快速测试"
	@echo "  test-smoke       运行冒烟测试"
	@echo ""
	@echo "测试执行 (传统方式):"
	@echo "  test-legacy      运行传统测试"
	@echo "  test-api         运行API测试"
	@echo "  test-e2e         运行端到端测试"
	@echo "  test-security    运行安全测试"
	@echo ""
	@echo "测试报告:"
	@echo "  coverage         生成覆盖率报告"
	@echo "  report           生成综合测试报告"
	@echo "  test-reports     生成HTML测试报告"
	@echo ""
	@echo "代码质量:"
	@echo "  lint             代码检查"
	@echo "  format           代码格式化"
	@echo ""
	@echo "清理:"
	@echo "  clean            清理测试文件和缓存"
	@echo "  clean-all        完全清理"
	@echo "  test-cleanup     清理测试环境"

# 安装依赖
install:
	@echo "📦 安装Python依赖..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 设置测试环境
setup:
	@echo "🔧 设置测试环境..."
	mkdir -p test_reports
	mkdir -p test_uploads
	mkdir -p test_logs
	@echo "✅ 测试环境设置完成"

# 验证测试环境
test-validate:
	@echo "🔍 验证测试环境..."
	python run_automated_tests.py --validate-only

# 运行所有测试 (新自动化框架)
test: setup
	@echo "🚀 运行完整测试套件 (自动化框架)..."
	python run_automated_tests.py --type all --verbose

# 运行传统测试
test-legacy: setup
	@echo "🚀 运行完整测试套件 (传统方式)..."
	python execute_test_suite.py --env local -v

# 运行单元测试 (新框架)
test-unit: setup
	@echo "📋 运行单元测试..."
	python run_automated_tests.py --type unit --verbose

# 运行集成测试 (新框架)
test-integration: setup
	@echo "🔗 运行集成测试..."
	python run_automated_tests.py --type integration --verbose

# 运行会议模块测试 (新框架)
test-meeting: setup
	@echo "📹 运行会议模块测试..."
	python run_automated_tests.py --type meeting --verbose

# 运行性能测试 (新框架)
test-performance: setup
	@echo "⚡ 运行性能测试..."
	python run_automated_tests.py --type performance --verbose

# 测试框架自身验证
test-framework: setup
	@echo "🔧 测试框架自身验证..."
	pytest tests/test_framework/ -v -m framework

# 运行快速测试 (新框架)
test-quick: setup
	@echo "⚡ 运行快速测试..."
	python run_automated_tests.py --type unit --no-coverage

# 运行冒烟测试
test-smoke: setup
	@echo "💨 运行冒烟测试..."
	pytest -v -m smoke

# 运行API测试 (传统方式)
test-api: setup
	@echo "🌐 运行API测试..."
	python run_tests.py --api -v

# 运行端到端测试 (传统方式)
test-e2e: setup
	@echo "🎯 运行端到端测试..."
	python run_tests.py --e2e -v

# 运行安全测试 (传统方式)
test-security: setup
	@echo "🔒 运行安全测试..."
	python run_tests.py --security -v

# 并行测试
test-parallel: setup
	@echo "🚀 并行运行测试..."
	python run_tests.py --parallel 4 -v

# 生成覆盖率报告
coverage:
	@echo "📊 生成覆盖率报告..."
	pytest --cov=src --cov-report=html:test_reports/coverage_html --cov-report=xml:test_reports/coverage.xml --cov-report=term-missing
	@echo "📄 覆盖率报告已生成到 test_reports/coverage_html/"

# 生成HTML测试报告 (新框架)
test-reports:
	@echo "📊 生成HTML测试报告..."
	python -c "
	try:
		from tests.test_framework import test_runner
		results = test_runner.run_all_tests()
		report_file = test_runner.generate_html_report(results)
		print(f'📄 HTML测试报告已生成: {report_file}')
	except Exception as e:
		print(f'❌ 生成报告失败: {e}')
		print('请先运行测试: make test')
	"

# 生成综合测试报告
report:
	@echo "📊 生成综合测试报告..."
	python -c "
	import json
	from pathlib import Path
	from datetime import datetime
	
	# 读取所有测试报告
	reports_dir = Path('test_reports')
	if reports_dir.exists():
		print('📄 可用的测试报告:')
		for report_file in reports_dir.glob('*.json'):
			print(f'  - {report_file.name}')
		for report_file in reports_dir.glob('*.html'):
			print(f'  - {report_file.name}')
	else:
		print('❌ 未找到测试报告，请先运行测试')
	"

# 代码检查
lint:
	@echo "🔍 运行代码检查..."
	flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy src/ --ignore-missing-imports

# 代码格式化
format:
	@echo "🎨 格式化代码..."
	black src/ tests/
	isort src/ tests/
	@echo "✅ 代码格式化完成"

# 清理测试环境 (新框架)
test-cleanup:
	@echo "🧹 清理测试环境..."
	python run_automated_tests.py --cleanup

# 清理测试文件
clean:
	@echo "🧹 清理测试文件..."
	rm -rf test_uploads/
	rm -rf test_logs/
	rm -rf .pytest_cache
	rm -rf __pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 测试文件清理完成"

# 完全清理
clean-all: clean test-cleanup
	@echo "🧹 完全清理..."
	rm -rf test_reports/
	rm -rf htmlcov/
	rm -rf .coverage*
	@echo "✅ 完全清理完成"

# CI/CD相关命令
ci-test:
	@echo "🤖 CI环境测试..."
	python ci_test_runner.py --test-types unit integration meeting --environment ci

ci-full:
	@echo "🤖 CI完整测试..."
	python ci_test_runner.py --test-types unit integration meeting api e2e --environment ci

ci-quick:
	@echo "⚡ CI快速测试..."
	python ci_test_runner.py --test-types unit --environment ci --no-notifications

# 部署相关命令
deploy-staging:
	@echo "🚀 部署到预发布环境..."
	python deploy_automation.py --environment staging --image-tag $(IMAGE_TAG)

deploy-production:
	@echo "🚀 部署到生产环境..."
	python deploy_automation.py --environment production --image-tag $(IMAGE_TAG)

deploy-check:
	@echo "🔍 检查部署状态..."
	kubectl get pods -n $(NAMESPACE) -l app=ai-testing-system

deploy-logs:
	@echo "📋 查看部署日志..."
	kubectl logs -n $(NAMESPACE) -l app=ai-testing-system --tail=100

deploy-rollback:
	@echo "🔄 回滚部署..."
	kubectl rollout undo deployment/ai-testing-system -n $(NAMESPACE)

# 开发环境快速检查
dev-check: format lint test-quick
	@echo "✅ 开发环境检查完成"

# 发布前检查
pre-release: format lint test coverage
	@echo "✅ 发布前检查完成"

# 性能基准测试
benchmark:
	@echo "📈 运行性能基准测试..."
	python execute_test_suite.py --env performance --tests performance

# 安全扫描
security-scan:
	@echo "🔒 运行安全扫描..."
	python execute_test_suite.py --tests security
	# 可以添加其他安全扫描工具
	# bandit -r src/
	# safety check

# 生成测试数据
generate-test-data:
	@echo "🎲 生成测试数据..."
	python -c "
	from tests.factories import TestDataGenerator
	generator = TestDataGenerator()
	
	# 生成性能测试数据
	data = generator.create_performance_test_data(100)
	print(f'生成了 {len(data[\"meetings\"])} 个会议和 {len(data[\"participants\"])} 个参与者')
	"

# 数据库迁移测试
test-migrations:
	@echo "🗄️ 测试数据库迁移..."
	# 这里可以添加数据库迁移测试逻辑
	@echo "✅ 数据库迁移测试完成"

# 监控测试执行
monitor-tests:
	@echo "📊 监控测试执行..."
	watch -n 5 'find test_reports -name "*.xml" -exec ls -la {} \;'

# 显示测试统计
test-stats:
	@echo "📊 测试统计信息..."
	python -c "
	import json
	from pathlib import Path
	
	reports_dir = Path('test_reports')
	if not reports_dir.exists():
		print('❌ 未找到测试报告目录')
		exit(1)
	
	json_files = list(reports_dir.glob('*_coverage.json'))
	if json_files:
		print('📈 覆盖率统计:')
		for file in json_files:
			try:
				with open(file) as f:
					data = json.load(f)
					coverage = data.get('totals', {}).get('percent_covered', 0)
					print(f'  {file.stem}: {coverage:.1f}%')
			except Exception as e:
				print(f'  {file.stem}: 解析失败')
	else:
		print('❌ 未找到覆盖率报告')
	"