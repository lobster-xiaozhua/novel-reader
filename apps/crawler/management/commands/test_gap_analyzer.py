import ast
import re
import importlib
from pathlib import Path
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.conf import settings


RISK_WEIGHTS = {
    'no_test_file': 50,
    'security_sensitive': 30,
    'concurrency': 20,
    'core_shared': 15,
    'parsing_logic': 10,
    'data_validation': 10,
    'branch': 5,
    'exception_handler': 5,
}

SECURITY_DECORATORS = {'login_required', 'permission_required', 'require_POST', 'require_GET'}
SECURITY_FUNCTIONS = {
    'validate_crawl_url', 'authenticate', 'url_has_allowed_host_and_scheme',
    'check_password', 'make_password', 'validate_slug',
}
CONCURRENCY_IMPORTS = {'threading', 'asyncio', 'multiprocessing', 'concurrent'}
PARSING_IMPORTS = {'BeautifulSoup', 'lxml', 're', 'json', 'csv', 'xml'}
VALIDATION_PATTERNS = {
    'clean_', 'validate_', 'is_valid', 'form.is_valid', 'cleaned_data',
    'save(commit=', 'get_or_create', 'update_or_create',
}

SKIP_DIRS = {'migrations', '__pycache__', 'management', 'templatetags'}
SKIP_FILES = {'__init__.py', 'apps.py', 'admin.py', 'wsgi.py'}
CORE_MODULE_PREFIXES = ('utils/',)


class ModuleAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath, module_name):
        self.filepath = filepath
        self.module_name = module_name
        self.functions = []
        self.classes = []
        self.imports = set()
        self._current_class = None
        self._current_decorators = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        decorators = []
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decorators.append(d.id)
            elif isinstance(d, ast.Attribute):
                decorators.append(d.attr)
            elif isinstance(d, ast.Call):
                if isinstance(d.func, ast.Name):
                    decorators.append(d.func.id)
                elif isinstance(d.func, ast.Attribute):
                    decorators.append(d.func.attr)

        branches = sum(1 for child in ast.walk(node) if isinstance(child, (ast.If, ast.IfExp)))
        exceptions = sum(1 for child in ast.walk(node) if isinstance(child, ast.ExceptHandler))
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)

        self.functions.append({
            'name': node.name,
            'class': self._current_class,
            'line': node.lineno,
            'decorators': decorators,
            'branches': branches,
            'exceptions': exceptions,
            'calls': calls,
            'is_private': node.name.startswith('_') and not node.name.startswith('__'),
        })
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        prev_class = self._current_class
        self._current_class = node.name
        methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.classes.append({
            'name': node.name,
            'line': node.lineno,
            'methods': methods,
        })
        self.generic_visit(node)
        self._current_class = prev_class


class Command(BaseCommand):
    help = '分析测试覆盖缺口，识别高风险未测试代码路径并生成测试'

    def add_arguments(self, parser):
        parser.add_argument('--generate', action='store_true', help='为识别的缺口生成测试文件')
        parser.add_argument('--dry-run', action='store_true', help='仅分析，不写入任何文件')
        parser.add_argument('--min-risk', type=int, default=30, help='最低风险分数阈值（默认30）')
        parser.add_argument('--module', type=str, help='仅分析指定模块路径，如 apps.books')

    def handle(self, *args, **options):
        project_root = Path(settings.BASE_DIR)
        self.stdout.write(self.style.MIGRATE_HEADING('\n🔍 测试缺口分析器启动\n'))

        source_dirs = [project_root / 'apps', project_root / 'utils']
        findings = []

        for src_dir in source_dirs:
            if not src_dir.exists():
                continue
            for py_file in sorted(src_dir.rglob('*.py')):
                rel = py_file.relative_to(project_root)
                if self._should_skip(rel):
                    continue
                if options['module'] and not str(rel).startswith(options['module'].replace('.', '/')):
                    continue
                finding = self._analyze_file(py_file, rel, project_root)
                if finding:
                    findings.append(finding)

        findings.sort(key=lambda x: x['risk_score'], reverse=True)
        self._report(findings, options)

        if options['generate'] and not options['dry_run']:
            self._generate_tests(findings, project_root)

        self.stdout.write(self.style.SUCCESS('\n✅ 分析完成\n'))

    def _should_skip(self, rel_path):
        parts = rel_path.parts
        if any(d in SKIP_DIRS for d in parts):
            return True
        if rel_path.name in SKIP_FILES:
            return True
        if rel_path.name.startswith('test_'):
            return True
        return False

    def _analyze_file(self, filepath, rel_path, project_root):
        try:
            source = filepath.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError) as e:
            self.stderr.write(f'  ⚠ 解析失败 {rel_path}: {e}')
            return None

        module_name = '.'.join(rel_path.with_suffix('').parts)
        analyzer = ModuleAnalyzer(filepath, module_name)
        analyzer.visit(tree)

        test_file = self._find_test_file(rel_path, project_root)
        has_test = test_file is not None

        risk_score = 0
        risk_factors = []

        if not has_test:
            risk_score += RISK_WEIGHTS['no_test_file']
            risk_factors.append('无测试文件')

        is_core = str(rel_path).startswith(CORE_MODULE_PREFIXES)
        if is_core:
            risk_score += RISK_WEIGHTS['core_shared']
            risk_factors.append('核心共享模块')

        has_concurrency = bool(analyzer.imports & CONCURRENCY_IMPORTS)
        if has_concurrency:
            risk_score += RISK_WEIGHTS['concurrency']
            risk_factors.append('并发逻辑')

        has_parsing = bool(analyzer.imports & PARSING_IMPORTS)
        if has_parsing:
            risk_score += RISK_WEIGHTS['parsing_logic']
            risk_factors.append('解析逻辑')

        security_funcs = []
        validation_funcs = []
        for func in analyzer.functions:
            if any(d in SECURITY_DECORATORS for d in func['decorators']):
                risk_score += RISK_WEIGHTS['security_sensitive']
                security_funcs.append(func['name'] if not func['class'] else f"{func['class']}.{func['name']}")
            if func['name'] in SECURITY_FUNCTIONS or func['name'] in func['calls']:
                risk_score += RISK_WEIGHTS['security_sensitive']
                security_funcs.append(func['name'])
            if any(p in func['name'] for p in ('validate_', 'clean_', 'is_valid')):
                risk_score += RISK_WEIGHTS['data_validation']
                validation_funcs.append(func['name'])
            risk_score += func['branches'] * RISK_WEIGHTS['branch']
            risk_score += func['exceptions'] * RISK_WEIGHTS['exception_handler']

        if security_funcs:
            risk_factors.append(f'安全敏感: {", ".join(security_funcs[:3])}')
        if validation_funcs:
            risk_factors.append(f'数据验证: {", ".join(validation_funcs[:3])}')

        untested_funcs = []
        for func in analyzer.functions:
            if func['is_private'] and func['branches'] < 2 and not func['exceptions']:
                continue
            untested_funcs.append({
                'name': f"{func['class']}.{func['name']}" if func['class'] else func['name'],
                'line': func['line'],
                'branches': func['branches'],
                'exceptions': func['exceptions'],
                'decorators': func['decorators'],
            })

        return {
            'module': module_name,
            'path': str(rel_path),
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'has_test': has_test,
            'test_file': str(test_file.relative_to(project_root)) if test_file else None,
            'classes': analyzer.classes,
            'untested_funcs': untested_funcs,
            'imports': analyzer.imports,
        }

    def _find_test_file(self, rel_path, project_root):
        stem = rel_path.stem
        parent = rel_path.parent

        candidates = [
            project_root / parent / f'test_{stem}.py',
            project_root / 'tests' / f'test_{stem}.py',
            project_root / parent / 'tests' / f'test_{stem}.py',
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _report(self, findings, options):
        if not findings:
            self.stdout.write(self.style.SUCCESS('  未发现高风险覆盖缺口'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('  ┌─────────────────────────────────────────────────────────────────┐'))
        self.stdout.write(self.style.MIGRATE_HEADING('  │                    测试缺口分析报告                            │'))
        self.stdout.write(self.style.MIGRATE_HEADING('  └─────────────────────────────────────────────────────────────────┘\n'))

        for i, f in enumerate(findings, 1):
            risk_label = self._risk_label(f['risk_score'])
            self.stdout.write(f'  {i}. [{risk_label}] {f["module"]} (风险分: {f["risk_score"]})')
            self.stdout.write(f'     路径: {f["path"]}')
            self.stdout.write(f'     因素: {" | ".join(f["risk_factors"])}')
            if f['untested_funcs']:
                self.stdout.write(f'     未覆盖函数:')
                for func in f['untested_funcs'][:8]:
                    detail = []
                    if func['branches']:
                        detail.append(f'{func["branches"]}分支')
                    if func['exceptions']:
                        detail.append(f'{func["exceptions"]}异常')
                    if func['decorators']:
                        detail.append(f'@{",@".join(func["decorators"][:2])}')
                    detail_str = f' ({", ".join(detail)})' if detail else ''
                    self.stdout.write(f'       - {func["name"]}:L{func["line"]}{detail_str}')
                if len(f['untested_funcs']) > 8:
                    self.stdout.write(f'       ... 及其他 {len(f["untested_funcs"]) - 8} 个函数')
            self.stdout.write('')

        total = len(findings)
        high = sum(1 for f in findings if f['risk_score'] >= 80)
        medium = sum(1 for f in findings if 50 <= f['risk_score'] < 80)
        low = sum(1 for f in findings if f['risk_score'] < 50)
        self.stdout.write(f'  统计: {total} 个模块存在缺口 | 🔴 高风险: {high} | 🟡 中风险: {medium} | 🟢 低风险: {low}')
        self.stdout.write(f'  阈值: 最低风险分 {options["min_risk"]}\n')

    def _risk_label(self, score):
        if score >= 80:
            return '🔴 高风险'
        elif score >= 50:
            return '🟡 中风险'
        return '🟢 低风险'

    def _generate_tests(self, findings, project_root):
        tests_dir = project_root / 'tests'
        tests_dir.mkdir(exist_ok=True)

        generated = []
        for f in findings:
            if f['risk_score'] < 30:
                continue
            stem = Path(f['path']).stem
            test_filename = f'test_{stem}.py'
            test_filepath = tests_dir / test_filename

            if test_filepath.exists():
                self.stdout.write(f'  ⏭ 测试文件已存在: {test_filepath}')
                continue

            content = self._build_test_content(f)
            test_filepath.write_text(content, encoding='utf-8')
            generated.append(test_filepath)
            self.stdout.write(self.style.SUCCESS(f'  ✅ 生成: {test_filepath.relative_to(project_root)}'))

        if generated:
            self.stdout.write(f'\n  共生成 {len(generated)} 个测试文件')
            self.stdout.write('  运行测试: pytest tests/ -v\n')

    def _build_test_content(self, finding):
        module_path = finding['module']
        imports = ['import pytest', 'from django.test import RequestFactory, Client, TestCase']
        has_model = any(c['name'] for c in finding['classes']
                        if any(m in c.get('methods', []) for m in ('save', '__str__', 'Meta')))

        if 'django.contrib.auth' in finding.get('imports', set()) or any(
            'login_required' in func.get('decorators', []) for func in finding['untested_funcs']
        ):
            imports.append('from django.contrib.auth.models import User')

        module_import = f'from {module_path} import *'
        imports.append(module_import)

        lines = ['"""', f'测试覆盖缺口: {module_path}', f'风险分: {finding["risk_score"]}',
                 f'风险因素: {", ".join(finding["risk_factors"])}', '"""', '']
        lines.extend(imports)
        lines.append('')
        lines.append('')

        for func in finding['untested_funcs']:
            func_name = func['name'].split('.')[-1] if '.' in func['name'] else func['name']
            class_name = func['name'].rsplit('.', 1)[0] if '.' in func['name'] else None

            if class_name:
                test_class_name = f'Test{class_name}'
            else:
                test_class_name = f'Test{func_name.title().replace("_", "")}'

            method_name = f'test_{func_name}'

            if any(d in SECURITY_DECORATORS for d in func.get('decorators', [])):
                lines.extend(self._gen_auth_test(test_class_name, method_name, func_name, class_name))
            elif func['branches'] >= 3 or func['exceptions'] >= 2:
                lines.extend(self._gen_complex_test(test_class_name, method_name, func_name, class_name, func))
            else:
                lines.extend(self._gen_basic_test(test_class_name, method_name, func_name, class_name))

            lines.append('')

        return '\n'.join(lines)

    def _gen_auth_test(self, class_name, method_name, func_name, class_name_attr):
        return [
            f'class {class_name}(TestCase):',
            f'    def setUp(self):',
            f'        self.client = Client()',
            f'        self.user = User.objects.create_user("testuser", password="testpass123")',
            '',
            f'    def {method_name}_unauthenticated(self):',
            f'        """未认证用户应被重定向到登录页"""',
            f'        pass',
            '',
            f'    def {method_name}_authenticated(self):',
            f'        """认证用户应能正常访问"""',
            f'        self.client.force_login(self.user)',
            f'        pass',
        ]

    def _gen_complex_test(self, class_name, method_name, func_name, class_name_attr, func_info):
        lines = [
            f'class {class_name}(TestCase):',
            f'    def {method_name}_happy_path(self):',
            f'        """正常路径测试"""',
            f'        pass',
            '',
        ]
        if func_info['branches']:
            lines.extend([
                f'    def {method_name}_edge_cases(self):',
                f'        """边界条件测试（{func_info["branches"]}个分支）"""',
                f'        pass',
                '',
            ])
        if func_info['exceptions']:
            lines.extend([
                f'    def {method_name}_error_handling(self):',
                f'        """异常处理测试（{func_info["exceptions"]}个异常捕获）"""',
                f'        pass',
                '',
            ])
        return lines

    def _gen_basic_test(self, class_name, method_name, func_name, class_name_attr):
        return [
            f'class {class_name}(TestCase):',
            f'    def {method_name}(self):',
            f'        """测试 {func_name} 基本行为"""',
            f'        pass',
        ]
