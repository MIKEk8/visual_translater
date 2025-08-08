#!/usr/bin/env python3
"""
Performance Analysis Tool for Screen Translator v2.0
Analyzes code for performance bottlenecks, memory usage patterns, and optimization opportunities
"""

import ast
import os
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter


class PerformanceAnalyzer(ast.NodeVisitor):
    """Analyzes Python code for performance issues"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues = []
        self.loops = []
        self.function_calls = []
        self.large_data_structures = []
        self.io_operations = []
        self.memory_patterns = []
        self.current_function = None
        self.current_class = None
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        
        # Check for complex functions (many statements)
        total_statements = sum(1 for _ in ast.walk(node) if isinstance(_, ast.stmt))
        if total_statements > 50:
            self.issues.append({
                'type': 'complex_function',
                'severity': 'medium',
                'function': node.name,
                'class': self.current_class,
                'statements': total_statements,
                'line': node.lineno,
                'message': f"Function '{node.name}' has {total_statements} statements (consider refactoring)"
            })
        
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_For(self, node):
        """Analyze for loops for performance issues"""
        self.loops.append({
            'type': 'for',
            'line': node.lineno,
            'function': self.current_function,
            'class': self.current_class
        })
        
        # Check for nested loops
        nested_loops = [n for n in ast.walk(node) if isinstance(n, (ast.For, ast.While)) and n != node]
        if nested_loops:
            self.issues.append({
                'type': 'nested_loops',
                'severity': 'high',
                'line': node.lineno,
                'function': self.current_function,
                'class': self.current_class,
                'nested_count': len(nested_loops),
                'message': f"Nested loops detected (O(n^{len(nested_loops)+1}) complexity)"
            })
        
        self.generic_visit(node)
        
    def visit_While(self, node):
        """Analyze while loops"""
        self.loops.append({
            'type': 'while',
            'line': node.lineno,
            'function': self.current_function,
            'class': self.current_class
        })
        self.generic_visit(node)
        
    def visit_ListComp(self, node):
        """Analyze list comprehensions"""
        # Check for complex list comprehensions
        generators = node.generators
        if len(generators) > 2:
            self.issues.append({
                'type': 'complex_comprehension',
                'severity': 'medium',
                'line': node.lineno,
                'function': self.current_function,
                'class': self.current_class,
                'generators': len(generators),
                'message': f"Complex list comprehension with {len(generators)} generators"
            })
        
        self.generic_visit(node)
        
    def visit_Call(self, node):
        """Analyze function calls for performance issues"""
        func_name = self._get_call_name(node)
        
        if func_name:
            self.function_calls.append({
                'name': func_name,
                'line': node.lineno,
                'function': self.current_function,
                'class': self.current_class
            })
            
            # Check for potentially expensive operations
            expensive_ops = {
                'time.sleep': 'blocking_operation',
                'input': 'blocking_operation',
                'print': 'io_operation',
                'open': 'io_operation',
                'json.loads': 'parsing_operation',
                'json.dumps': 'parsing_operation',
                'pickle.loads': 'parsing_operation',
                'pickle.dumps': 'parsing_operation',
                're.compile': 'regex_compilation',
                'sorted': 'sorting_operation',
                'max': 'aggregation_operation',
                'min': 'aggregation_operation',
                'sum': 'aggregation_operation'
            }
            
            for op, op_type in expensive_ops.items():
                if func_name == op or func_name.endswith(f'.{op.split(".")[-1]}'):
                    self.io_operations.append({
                        'operation': func_name,
                        'type': op_type,
                        'line': node.lineno,
                        'function': self.current_function,
                        'class': self.current_class
                    })
        
        self.generic_visit(node)
        
    def visit_List(self, node):
        """Check for large list literals"""
        if len(node.elts) > 100:
            self.large_data_structures.append({
                'type': 'large_list',
                'size': len(node.elts),
                'line': node.lineno,
                'function': self.current_function,
                'class': self.current_class
            })
        self.generic_visit(node)
        
    def visit_Dict(self, node):
        """Check for large dictionary literals"""
        if len(node.keys) > 50:
            self.large_data_structures.append({
                'type': 'large_dict',
                'size': len(node.keys),
                'line': node.lineno,
                'function': self.current_function,
                'class': self.current_class
            })
        self.generic_visit(node)
        
    def visit_Assign(self, node):
        """Check for memory allocation patterns"""
        # Check for potential memory leaks (large objects without explicit cleanup)
        if isinstance(node.value, ast.Call):
            func_name = self._get_call_name(node.value)
            memory_heavy_ops = [
                'Image.new', 'np.zeros', 'np.ones', 'np.array', 'cv2.imread',
                'bytearray', 'list', 'dict', 'set'
            ]
            
            for op in memory_heavy_ops:
                if func_name and (func_name == op or func_name.endswith(f'.{op.split(".")[-1]}')):
                    self.memory_patterns.append({
                        'type': 'memory_allocation',
                        'operation': func_name,
                        'line': node.lineno,
                        'function': self.current_function,
                        'class': self.current_class
                    })
        
        self.generic_visit(node)
        
    def _get_call_name(self, node):
        """Get the name of a function call"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            value_name = self._get_attr_name(node.func.value)
            return f"{value_name}.{node.func.attr}" if value_name else node.func.attr
        return None
        
    def _get_attr_name(self, node):
        """Get the name of an attribute access"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_attr_name(node.value)
            return f"{value_name}.{node.attr}" if value_name else node.attr
        return None
        
    def get_report(self) -> Dict:
        """Generate performance analysis report"""
        return {
            'file': self.file_path,
            'issues': self.issues,
            'loops': self.loops,
            'function_calls': self.function_calls,
            'large_data_structures': self.large_data_structures,
            'io_operations': self.io_operations,
            'memory_patterns': self.memory_patterns,
            'summary': {
                'total_issues': len(self.issues),
                'loop_count': len(self.loops),
                'function_call_count': len(self.function_calls),
                'io_operation_count': len(self.io_operations),
                'large_structures_count': len(self.large_data_structures),
                'memory_allocations': len(self.memory_patterns)
            }
        }


def analyze_file_performance(file_path: str) -> Dict:
    """Analyze performance for a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        analyzer = PerformanceAnalyzer(file_path)
        analyzer.visit(tree)
        
        return analyzer.get_report()
        
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e),
            'issues': [],
            'loops': [],
            'function_calls': [],
            'large_data_structures': [],
            'io_operations': [],
            'memory_patterns': [],
            'summary': {}
        }


def check_file_sizes() -> Dict:
    """Check for large files that might impact performance"""
    large_files = []
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    total_size += size
                    file_count += 1
                    
                    if size > 50000:  # Files larger than 50KB
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = len(f.readlines())
                        
                        large_files.append({
                            'file': file_path,
                            'size_bytes': size,
                            'size_kb': size / 1024,
                            'lines': lines
                        })
                except Exception:
                    continue
    
    return {
        'large_files': sorted(large_files, key=lambda x: x['size_bytes'], reverse=True),
        'total_size_kb': total_size / 1024,
        'average_size_kb': (total_size / file_count / 1024) if file_count > 0 else 0,
        'file_count': file_count
    }


def analyze_imports_performance() -> Dict:
    """Analyze import patterns that might affect startup performance"""
    import_issues = []
    
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Check for imports in the middle of the file
                    in_function = False
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if line.startswith('def ') or line.startswith('class '):
                            in_function = True
                        elif line.startswith('import ') or line.startswith('from '):
                            if in_function and not line.startswith('#'):
                                import_issues.append({
                                    'file': file_path,
                                    'line': i + 1,
                                    'import': line,
                                    'issue': 'import_in_function'
                                })
                    
                    # Check for expensive imports
                    expensive_imports = [
                        'numpy', 'cv2', 'PIL', 'matplotlib', 'scipy',
                        'tensorflow', 'torch', 'sklearn'
                    ]
                    
                    for i, line in enumerate(lines):
                        for exp_import in expensive_imports:
                            if f'import {exp_import}' in line or f'from {exp_import}' in line:
                                import_issues.append({
                                    'file': file_path,
                                    'line': i + 1,
                                    'import': line.strip(),
                                    'issue': 'expensive_import'
                                })
                
                except Exception:
                    continue
    
    return {
        'import_issues': import_issues,
        'issues_by_type': Counter(issue['issue'] for issue in import_issues)
    }


def analyze_project_performance() -> Dict:
    """Analyze performance for entire project"""
    print("🔍 Analyzing Performance in Screen Translator v2.0...")
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                python_files.append(os.path.join(root, file))
    
    print(f"📁 Found {len(python_files)} Python files to analyze")
    
    # Analyze each file
    file_reports = []
    all_issues = []
    all_loops = []
    all_io_ops = []
    all_memory_patterns = []
    
    for file_path in python_files:
        report = analyze_file_performance(file_path)
        file_reports.append(report)
        
        all_issues.extend(report.get('issues', []))
        all_loops.extend(report.get('loops', []))
        all_io_ops.extend(report.get('io_operations', []))
        all_memory_patterns.extend(report.get('memory_patterns', []))
    
    # Additional analyses
    file_sizes = check_file_sizes()
    import_analysis = analyze_imports_performance()
    
    # Categorize issues by severity
    issues_by_severity = defaultdict(list)
    for issue in all_issues:
        issues_by_severity[issue.get('severity', 'low')].append(issue)
    
    # Find most problematic files
    files_by_issues = defaultdict(int)
    for issue in all_issues:
        if 'file' in issue:
            files_by_issues[issue['file']] += 1
    
    most_problematic = sorted(files_by_issues.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'files_analyzed': len(python_files),
        'file_reports': file_reports,
        'file_sizes': file_sizes,
        'import_analysis': import_analysis,
        'aggregate': {
            'total_issues': len(all_issues),
            'issues_by_severity': dict(issues_by_severity),
            'total_loops': len(all_loops),
            'total_io_operations': len(all_io_ops),
            'total_memory_patterns': len(all_memory_patterns),
            'most_problematic_files': most_problematic[:10]
        }
    }


def print_performance_report(analysis: Dict):
    """Print formatted performance analysis report"""
    print("\n" + "="*60)
    print("⚡ PERFORMANCE ANALYSIS REPORT")
    print("="*60)
    
    agg = analysis['aggregate']
    
    print(f"\n📊 SUMMARY:")
    print(f"  Files analyzed: {analysis['files_analyzed']}")
    print(f"  Total performance issues: {agg['total_issues']}")
    print(f"  High severity: {len(agg['issues_by_severity'].get('high', []))}")
    print(f"  Medium severity: {len(agg['issues_by_severity'].get('medium', []))}")
    print(f"  Low severity: {len(agg['issues_by_severity'].get('low', []))}")
    print(f"  Total loops: {agg['total_loops']}")
    print(f"  I/O operations: {agg['total_io_operations']}")
    print(f"  Memory allocations: {agg['total_memory_patterns']}")
    
    # File size analysis
    file_sizes = analysis['file_sizes']
    print(f"\n📁 FILE SIZE ANALYSIS:")
    print(f"  Total codebase size: {file_sizes['total_size_kb']:.1f} KB")
    print(f"  Average file size: {file_sizes['average_size_kb']:.1f} KB")
    print(f"  Large files (>50KB): {len(file_sizes['large_files'])}")
    
    if file_sizes['large_files']:
        print(f"\n📋 LARGEST FILES:")
        for file_info in file_sizes['large_files'][:5]:
            file_short = file_info['file'].replace('src/', '')
            print(f"  {file_short}: {file_info['size_kb']:.1f} KB ({file_info['lines']} lines)")
    
    # High severity issues
    high_issues = agg['issues_by_severity'].get('high', [])
    if high_issues:
        print(f"\n🚨 HIGH SEVERITY ISSUES:")
        issue_types = Counter(issue['type'] for issue in high_issues)
        for issue_type, count in issue_types.most_common(5):
            print(f"  {issue_type}: {count} instances")
    
    # Most problematic files
    if agg['most_problematic_files']:
        print(f"\n📁 FILES WITH MOST ISSUES:")
        for file_path, issue_count in agg['most_problematic_files']:
            file_short = file_path.replace('src/', '')
            print(f"  {file_short}: {issue_count} issues")
    
    # Import analysis
    import_analysis = analysis['import_analysis']
    if import_analysis['import_issues']:
        print(f"\n📦 IMPORT PERFORMANCE ISSUES:")
        for issue_type, count in import_analysis['issues_by_type'].items():
            issue_desc = {
                'import_in_function': 'Imports inside functions',
                'expensive_import': 'Expensive imports detected'
            }
            print(f"  {issue_desc.get(issue_type, issue_type)}: {count}")
    
    # I/O operations analysis
    if all_io_ops := [op for report in analysis['file_reports'] for op in report.get('io_operations', [])]:
        io_types = Counter(op['type'] for op in all_io_ops)
        print(f"\n💾 I/O OPERATIONS:")
        for op_type, count in io_types.most_common(5):
            op_desc = {
                'blocking_operation': 'Blocking operations',
                'io_operation': 'File I/O operations',
                'parsing_operation': 'Parsing operations'
            }
            print(f"  {op_desc.get(op_type, op_type)}: {count}")
    
    # Performance recommendations
    print(f"\n🎯 PERFORMANCE ASSESSMENT:")
    
    risk_score = 0
    recommendations = []
    
    if len(high_issues) > 10:
        risk_score += 3
        recommendations.append("⚠️  Address high severity performance issues")
    elif len(high_issues) > 5:
        risk_score += 2
        recommendations.append("⚠️  Review high severity performance issues")
    
    if len(file_sizes['large_files']) > 10:
        risk_score += 2
        recommendations.append("⚠️  Consider splitting large files")
    elif len(file_sizes['large_files']) > 5:
        risk_score += 1
        recommendations.append("⚠️  Monitor large file growth")
    
    if agg['total_loops'] > 200:
        risk_score += 2
        recommendations.append("⚠️  High loop count - review algorithmic complexity")
    elif agg['total_loops'] > 100:
        risk_score += 1
        recommendations.append("⚠️  Moderate loop usage")
    
    if len(import_analysis['import_issues']) > 20:
        risk_score += 1
        recommendations.append("⚠️  Optimize import patterns for startup performance")
    
    if not recommendations:
        recommendations.append("✅ Performance patterns look reasonable")
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print(f"\n🏆 PERFORMANCE SCORE: {max(0, 10 - risk_score)}/10")
    
    if risk_score >= 6:
        print("🚨 RECOMMENDATION: Immediate performance optimization required")
    elif risk_score >= 4:
        print("⚠️  RECOMMENDATION: Performance review recommended")
    else:
        print("✅ RECOMMENDATION: Performance appears adequate")


if __name__ == "__main__":
    try:
        analysis = analyze_project_performance()
        print_performance_report(analysis)
        
        # Save detailed report
        import json
        with open('performance_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed report saved to: performance_analysis.json")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        exit(1)