#!/usr/bin/env python3
"""
Error Handling Analysis Tool for Screen Translator v2.0
Analyzes exception handling patterns, error recovery mechanisms, and robustness
"""

import ast
import os
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter


class ErrorHandlingAnalyzer(ast.NodeVisitor):
    """Analyzes Python code for error handling patterns"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.try_blocks = []
        self.exception_types = []
        self.bare_excepts = []
        self.finally_blocks = []
        self.raises = []
        self.current_function = None
        self.current_class = None
        self.error_patterns = []
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_Try(self, node):
        """Analyze try-except blocks"""
        try_info = {
            'line': node.lineno,
            'function': self.current_function,
            'class': self.current_class,
            'handlers': [],
            'finally_block': bool(node.finalbody),
            'else_block': bool(node.orelse),
            'statements_in_try': len(node.body)
        }
        
        # Analyze exception handlers
        for handler in node.handlers:
            handler_info = {
                'line': handler.lineno,
                'exception_type': None,
                'is_bare_except': handler.type is None,
                'variable_name': handler.name
            }
            
            if handler.type:
                handler_info['exception_type'] = self._get_exception_type(handler.type)
                self.exception_types.append({
                    'type': handler_info['exception_type'],
                    'line': handler.lineno,
                    'function': self.current_function,
                    'class': self.current_class
                })
            else:
                self.bare_excepts.append({
                    'line': handler.lineno,
                    'function': self.current_function,
                    'class': self.current_class
                })
                
            try_info['handlers'].append(handler_info)
            
        self.try_blocks.append(try_info)
        
        # Check for finally blocks
        if node.finalbody:
            self.finally_blocks.append({
                'line': node.lineno,
                'function': self.current_function,
                'class': self.current_class,
                'statements': len(node.finalbody)
            })
        
        self.generic_visit(node)
        
    def visit_Raise(self, node):
        """Analyze raise statements"""
        raise_info = {
            'line': node.lineno,
            'function': self.current_function,
            'class': self.current_class,
            'exception_type': None,
            'has_cause': node.cause is not None
        }
        
        if node.exc:
            if isinstance(node.exc, ast.Call):
                raise_info['exception_type'] = self._get_exception_type(node.exc.func)
            elif isinstance(node.exc, ast.Name):
                raise_info['exception_type'] = node.exc.id
                
        self.raises.append(raise_info)
        self.generic_visit(node)
        
    def visit_Call(self, node):
        """Check for logging in exception handlers"""
        func_name = self._get_call_name(node)
        
        if func_name and 'log' in func_name.lower():
            # Check if this logging call is inside an except block
            # This is a simplified check - would need more context analysis
            self.error_patterns.append({
                'type': 'logging_call',
                'function_name': func_name,
                'line': node.lineno,
                'function': self.current_function,
                'class': self.current_class
            })
            
        self.generic_visit(node)
        
    def _get_exception_type(self, node):
        """Extract exception type name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_attr_name(node.value)}.{node.attr}"
        return "Unknown"
        
    def _get_attr_name(self, node):
        """Get the name of an attribute access"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_attr_name(node.value)
            return f"{value_name}.{node.attr}" if value_name else node.attr
        return None
        
    def _get_call_name(self, node):
        """Get the name of a function call"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            value_name = self._get_attr_name(node.func.value)
            return f"{value_name}.{node.func.attr}" if value_name else node.func.attr
        return None
        
    def get_report(self) -> Dict:
        """Generate error handling analysis report"""
        return {
            'file': self.file_path,
            'try_blocks': self.try_blocks,
            'exception_types': self.exception_types,
            'bare_excepts': self.bare_excepts,
            'finally_blocks': self.finally_blocks,
            'raises': self.raises,
            'error_patterns': self.error_patterns,
            'summary': {
                'total_try_blocks': len(self.try_blocks),
                'total_exception_handlers': sum(len(t['handlers']) for t in self.try_blocks),
                'bare_except_count': len(self.bare_excepts),
                'finally_block_count': len(self.finally_blocks),
                'raise_statements': len(self.raises),
                'logging_calls': len([p for p in self.error_patterns if p['type'] == 'logging_call'])
            }
        }


def analyze_file_error_handling(file_path: str) -> Dict:
    """Analyze error handling for a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        analyzer = ErrorHandlingAnalyzer(file_path)
        analyzer.visit(tree)
        
        return analyzer.get_report()
        
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e),
            'try_blocks': [],
            'exception_types': [],
            'bare_excepts': [],
            'finally_blocks': [],
            'raises': [],
            'error_patterns': [],
            'summary': {}
        }


def check_exception_definitions() -> Dict:
    """Check for custom exception definitions"""
    custom_exceptions = []
    
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check if class inherits from Exception or its subclasses
                            for base in node.bases:
                                if isinstance(base, ast.Name):
                                    if 'Exception' in base.id or 'Error' in base.id:
                                        custom_exceptions.append({
                                            'name': node.name,
                                            'file': file_path,
                                            'line': node.lineno,
                                            'base_class': base.id
                                        })
                                        
                except Exception:
                    continue
                    
    return {'custom_exceptions': custom_exceptions}


def analyze_error_recovery_patterns() -> Dict:
    """Analyze error recovery and retry patterns"""
    recovery_patterns = []
    
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Look for common recovery patterns
                    patterns = {
                        'retry': [r'retry', r'attempt', r'tries'],
                        'fallback': [r'fallback', r'default', r'alternative'],
                        'circuit_breaker': [r'circuit.*breaker', r'breaker'],
                        'timeout': [r'timeout', r'deadline'],
                        'graceful_degradation': [r'graceful', r'degrade']
                    }
                    
                    import re
                    for i, line in enumerate(lines):
                        line_lower = line.lower()
                        for pattern_type, regexes in patterns.items():
                            for regex in regexes:
                                if re.search(regex, line_lower):
                                    recovery_patterns.append({
                                        'type': pattern_type,
                                        'file': file_path,
                                        'line': i + 1,
                                        'content': line.strip()
                                    })
                                    
                except Exception:
                    continue
                    
    return {
        'recovery_patterns': recovery_patterns,
        'patterns_by_type': Counter(p['type'] for p in recovery_patterns)
    }


def analyze_project_error_handling() -> Dict:
    """Analyze error handling for entire project"""
    print("🔍 Analyzing Error Handling in Screen Translator v2.0...")
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"📁 Found {len(python_files)} Python files to analyze")
    
    # Analyze each file
    file_reports = []
    all_try_blocks = []
    all_exception_types = []
    all_bare_excepts = []
    all_raises = []
    
    for file_path in python_files:
        report = analyze_file_error_handling(file_path)
        file_reports.append(report)
        
        all_try_blocks.extend(report.get('try_blocks', []))
        all_exception_types.extend(report.get('exception_types', []))
        all_bare_excepts.extend(report.get('bare_excepts', []))
        all_raises.extend(report.get('raises', []))
    
    # Additional analyses
    custom_exceptions = check_exception_definitions()
    recovery_patterns = analyze_error_recovery_patterns()
    
    # Analyze exception type patterns
    exception_type_counts = Counter(exc['type'] for exc in all_exception_types)
    
    # Find files with best/worst error handling
    files_by_coverage = []
    for report in file_reports:
        if 'summary' in report:
            summary = report['summary']
            total_handlers = summary.get('total_exception_handlers', 0)
            bare_excepts = summary.get('bare_except_count', 0)
            finally_blocks = summary.get('finally_block_count', 0)
            
            # Calculate error handling score
            score = 0
            score += total_handlers * 2  # Points for exception handling
            score += finally_blocks * 3  # Extra points for cleanup
            score -= bare_excepts * 5    # Penalty for bare excepts
            
            files_by_coverage.append({
                'file': report.get('file', ''),
                'score': score,
                'handlers': total_handlers,
                'bare_excepts': bare_excepts,
                'finally_blocks': finally_blocks
            })
    
    files_by_coverage.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'files_analyzed': len(python_files),
        'file_reports': file_reports,
        'custom_exceptions': custom_exceptions,
        'recovery_patterns': recovery_patterns,
        'aggregate': {
            'total_try_blocks': len(all_try_blocks),
            'total_exception_types': len(all_exception_types),
            'unique_exception_types': len(exception_type_counts),
            'total_bare_excepts': len(all_bare_excepts),
            'total_raises': len(all_raises),
            'exception_type_counts': dict(exception_type_counts.most_common(10)),
            'files_by_error_handling': files_by_coverage
        }
    }


def print_error_handling_report(analysis: Dict):
    """Print formatted error handling analysis report"""
    print("\n" + "="*60)
    print("🛡️  ERROR HANDLING ANALYSIS REPORT")
    print("="*60)
    
    agg = analysis['aggregate']
    
    print(f"\n📊 SUMMARY:")
    print(f"  Files analyzed: {analysis['files_analyzed']}")
    print(f"  Total try-except blocks: {agg['total_try_blocks']}")
    print(f"  Exception handlers: {agg['total_exception_types']}")
    print(f"  Unique exception types: {agg['unique_exception_types']}")
    print(f"  Bare except blocks: {agg['total_bare_excepts']}")
    print(f"  Raise statements: {agg['total_raises']}")
    
    # Custom exceptions
    custom_exceptions = analysis['custom_exceptions']['custom_exceptions']
    print(f"\n🎯 CUSTOM EXCEPTIONS:")
    print(f"  Custom exception classes: {len(custom_exceptions)}")
    
    if custom_exceptions:
        print(f"  Examples:")
        for exc in custom_exceptions[:5]:
            file_short = exc['file'].replace('src/', '')
            print(f"    - {exc['name']} ({exc['base_class']}) in {file_short}")
    
    # Most common exception types
    print(f"\n📈 MOST HANDLED EXCEPTION TYPES:")
    for exc_type, count in agg['exception_type_counts'].items():
        print(f"  {exc_type}: {count} handlers")
    
    # Recovery patterns
    recovery_patterns = analysis['recovery_patterns']
    print(f"\n🔄 ERROR RECOVERY PATTERNS:")
    print(f"  Total recovery patterns found: {len(recovery_patterns['recovery_patterns'])}")
    
    for pattern_type, count in recovery_patterns['patterns_by_type'].most_common():
        print(f"  {pattern_type}: {count} instances")
    
    # Files with best error handling
    print(f"\n🏆 FILES WITH BEST ERROR HANDLING:")
    for file_info in agg['files_by_error_handling'][:5]:
        if file_info['score'] > 0:
            file_short = file_info['file'].replace('src/', '')
            print(f"  {file_short}: score {file_info['score']} ({file_info['handlers']} handlers, {file_info['finally_blocks']} finally blocks)")
    
    # Files with poor error handling
    print(f"\n⚠️  FILES NEEDING ERROR HANDLING IMPROVEMENT:")
    poor_handling = [f for f in agg['files_by_error_handling'] if f['bare_excepts'] > 0 or f['score'] < 0]
    for file_info in poor_handling[-5:]:
        file_short = file_info['file'].replace('src/', '')
        issues = []
        if file_info['bare_excepts'] > 0:
            issues.append(f"{file_info['bare_excepts']} bare excepts")
        if file_info['handlers'] == 0:
            issues.append("no exception handling")
        print(f"  {file_short}: {', '.join(issues)}")
    
    # Error handling assessment
    print(f"\n🎯 ERROR HANDLING ASSESSMENT:")
    
    coverage_ratio = agg['total_exception_types'] / max(1, analysis['files_analyzed'])
    bare_except_ratio = agg['total_bare_excepts'] / max(1, agg['total_try_blocks'])
    
    issues = []
    
    if coverage_ratio < 2:
        issues.append("⚠️  Low exception handling coverage")
    elif coverage_ratio < 5:
        issues.append("⚠️  Moderate exception handling coverage")
    else:
        print("  ✅ Good exception handling coverage")
    
    if bare_except_ratio > 0.2:
        issues.append("⚠️  High ratio of bare except blocks")
    elif bare_except_ratio > 0.1:
        issues.append("⚠️  Some bare except blocks found")
    else:
        print("  ✅ Low bare except usage")
    
    if len(custom_exceptions) < 5:
        issues.append("⚠️  Few custom exception types defined")
    else:
        print("  ✅ Good custom exception usage")
    
    if len(recovery_patterns['recovery_patterns']) < 10:
        issues.append("⚠️  Limited error recovery patterns")
    else:
        print("  ✅ Good error recovery patterns")
    
    for issue in issues:
        print(f"  {issue}")
    
    # Overall assessment
    risk_score = 0
    risk_score += max(0, int(bare_except_ratio * 10))
    risk_score += max(0, 5 - int(coverage_ratio))
    risk_score += max(0, 3 - len(custom_exceptions) // 2)
    
    print(f"\n🏆 ERROR HANDLING ROBUSTNESS SCORE: {max(0, 10 - risk_score)}/10")
    
    if risk_score >= 6:
        print("🚨 RECOMMENDATION: Immediate error handling improvements required")
    elif risk_score >= 4:
        print("⚠️  RECOMMENDATION: Error handling review recommended")
    else:
        print("✅ RECOMMENDATION: Error handling appears robust")


if __name__ == "__main__":
    try:
        analysis = analyze_project_error_handling()
        print_error_handling_report(analysis)
        
        # Save detailed report
        import json
        with open('error_handling_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed report saved to: error_handling_analysis.json")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        exit(1)