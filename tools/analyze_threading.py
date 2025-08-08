#!/usr/bin/env python3
"""
Thread Safety Analysis Tool for Screen Translator v2.0
Analyzes potential race conditions and thread safety issues
"""

import ast
import glob
import os
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class ThreadSafetyAnalyzer(ast.NodeVisitor):
    """Analyzes Python code for thread safety issues"""
    
    def __init__(self):
        self.issues = []
        self.shared_variables = set()
        self.lock_usage = []
        self.thread_creations = []
        self.potential_races = []
        self.current_class = None
        self.current_method = None
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        old_method = self.current_method
        self.current_method = node.name
        self.generic_visit(node)
        self.current_method = old_method
        
    def visit_Assign(self, node):
        """Check for assignments to potentially shared variables"""
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                if isinstance(target.value, ast.Name) and target.value.id == 'self':
                    var_name = f"{self.current_class}.{target.attr}"
                    self.shared_variables.add(var_name)
                    
                    # Check if this assignment might be racy
                    if not self._is_protected_by_lock(node):
                        self.potential_races.append({
                            'type': 'unprotected_assignment',
                            'variable': var_name,
                            'class': self.current_class,
                            'method': self.current_method,
                            'line': node.lineno
                        })
        
        self.generic_visit(node)
        
    def visit_With(self, node):
        """Track with statements that might be locks"""
        for item in node.items:
            if isinstance(item.context_expr, ast.Attribute):
                if 'lock' in item.context_expr.attr.lower():
                    self.lock_usage.append({
                        'type': 'with_lock',
                        'class': self.current_class,
                        'method': self.current_method,
                        'line': node.lineno
                    })
        self.generic_visit(node)
        
    def visit_Call(self, node):
        """Track threading-related calls"""
        if isinstance(node.func, ast.Attribute):
            # Threading module calls
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'threading':
                if node.func.attr in ['Thread', 'Lock', 'RLock', 'Semaphore']:
                    self.thread_creations.append({
                        'type': node.func.attr,
                        'class': self.current_class,
                        'method': self.current_method,
                        'line': node.lineno
                    })
            
            # Check for acquire/release calls
            elif node.func.attr in ['acquire', 'release']:
                self.lock_usage.append({
                    'type': f'manual_{node.func.attr}',
                    'class': self.current_class,
                    'method': self.current_method,
                    'line': node.lineno
                })
                
        self.generic_visit(node)
        
    def _is_protected_by_lock(self, node):
        """Simple heuristic to check if code is in a lock context"""
        # This is a simplified check - would need more sophisticated analysis
        return False
        
    def get_report(self) -> Dict:
        """Generate thread safety analysis report"""
        return {
            'shared_variables': list(self.shared_variables),
            'lock_usage': self.lock_usage,
            'thread_creations': self.thread_creations,
            'potential_races': self.potential_races,
            'summary': {
                'total_shared_vars': len(self.shared_variables),
                'total_locks': len(self.lock_usage),
                'total_threads': len(self.thread_creations),
                'potential_race_conditions': len(self.potential_races)
            }
        }


def analyze_file(file_path: str) -> Dict:
    """Analyze a single Python file for thread safety"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        analyzer = ThreadSafetyAnalyzer()
        analyzer.visit(tree)
        
        report = analyzer.get_report()
        report['file'] = file_path
        return report
        
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e),
            'shared_variables': [],
            'lock_usage': [],
            'thread_creations': [],
            'potential_races': []
        }


def analyze_project() -> Dict:
    """Analyze entire project for thread safety"""
    print("🔍 Analyzing Thread Safety in Screen Translator v2.0...")
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                python_files.append(os.path.join(root, file))
    
    print(f"📁 Found {len(python_files)} Python files to analyze")
    
    # Analyze each file
    file_reports = []
    total_issues = 0
    
    for file_path in python_files:
        report = analyze_file(file_path)
        file_reports.append(report)
        total_issues += len(report.get('potential_races', []))
    
    # Aggregate results
    all_shared_vars = set()
    all_locks = []
    all_threads = []
    all_races = []
    
    for report in file_reports:
        all_shared_vars.update(report.get('shared_variables', []))
        all_locks.extend(report.get('lock_usage', []))
        all_threads.extend(report.get('thread_creations', []))
        all_races.extend(report.get('potential_races', []))
    
    return {
        'files_analyzed': len(python_files),
        'file_reports': file_reports,
        'aggregate': {
            'total_shared_variables': len(all_shared_vars),
            'total_lock_usage': len(all_locks),
            'total_thread_creations': len(all_threads),
            'total_potential_races': len(all_races),
            'shared_variables': list(all_shared_vars),
            'lock_usage': all_locks,
            'thread_creations': all_threads,
            'potential_races': all_races
        }
    }


def print_thread_safety_report(analysis: Dict):
    """Print formatted thread safety analysis report"""
    print("\n" + "="*60)
    print("🧵 THREAD SAFETY ANALYSIS REPORT")
    print("="*60)
    
    agg = analysis['aggregate']
    
    print(f"\n📊 SUMMARY:")
    print(f"  Files analyzed: {analysis['files_analyzed']}")
    print(f"  Shared variables: {agg['total_shared_variables']}")
    print(f"  Lock operations: {agg['total_lock_usage']}")
    print(f"  Thread creations: {agg['total_thread_creations']}")
    print(f"  Potential race conditions: {agg['total_potential_races']}")
    
    # Thread creations by file
    if agg['thread_creations']:
        print(f"\n🧵 THREAD USAGE:")
        thread_by_file = defaultdict(list)
        for thread in agg['thread_creations']:
            key = f"{thread.get('class', 'Global')}.{thread.get('method', 'N/A')}"
            thread_by_file[key].append(thread)
            
        for location, threads in thread_by_file.items():
            print(f"  {location}: {len(threads)} thread operations")
            for thread in threads[:3]:  # Show first 3
                print(f"    - {thread['type']} (line {thread['line']})")
    
    # Lock usage analysis
    if agg['lock_usage']:
        print(f"\n🔒 LOCK USAGE:")
        lock_by_file = defaultdict(list)
        for lock in agg['lock_usage']:
            key = f"{lock.get('class', 'Global')}.{lock.get('method', 'N/A')}"
            lock_by_file[key].append(lock)
            
        for location, locks in lock_by_file.items():
            print(f"  {location}: {len(locks)} lock operations")
            for lock in locks[:3]:  # Show first 3
                print(f"    - {lock['type']} (line {lock['line']})")
    
    # Potential race conditions
    if agg['potential_races']:
        print(f"\n⚠️  POTENTIAL RACE CONDITIONS:")
        race_by_severity = defaultdict(list)
        for race in agg['potential_races']:
            race_by_severity[race['type']].append(race)
            
        for race_type, races in race_by_severity.items():
            print(f"  {race_type}: {len(races)} instances")
            for race in races[:5]:  # Show first 5
                location = f"{race.get('class', 'Global')}.{race.get('method', 'N/A')}"
                print(f"    - {race['variable']} in {location} (line {race['line']})")
    
    # Files with most issues
    files_with_issues = []
    for report in analysis['file_reports']:
        issue_count = len(report.get('potential_races', []))
        if issue_count > 0:
            files_with_issues.append((report['file'], issue_count))
    
    if files_with_issues:
        files_with_issues.sort(key=lambda x: x[1], reverse=True)
        print(f"\n📁 FILES WITH MOST THREAD SAFETY ISSUES:")
        for file_path, issue_count in files_with_issues[:10]:
            relative_path = file_path.replace('src/', '')
            print(f"  {relative_path}: {issue_count} issues")
    
    # Risk assessment
    print(f"\n🎯 RISK ASSESSMENT:")
    risk_score = 0
    
    if agg['total_potential_races'] > 10:
        risk_score += 3
        print("  ⚠️  HIGH: Many potential race conditions detected")
    elif agg['total_potential_races'] > 5:
        risk_score += 2
        print("  ⚠️  MEDIUM: Some potential race conditions detected")
    elif agg['total_potential_races'] > 0:
        risk_score += 1
        print("  ⚠️  LOW: Few potential race conditions detected")
    else:
        print("  ✅ GOOD: No obvious race conditions detected")
    
    if agg['total_thread_creations'] > 20:
        risk_score += 2
        print("  ⚠️  HIGH: Heavy multithreading usage")
    elif agg['total_thread_creations'] > 10:
        risk_score += 1
        print("  ⚠️  MEDIUM: Moderate multithreading usage")
    else:
        print("  ✅ GOOD: Limited multithreading usage")
    
    if agg['total_lock_usage'] < agg['total_shared_variables'] / 2:
        risk_score += 2
        print("  ⚠️  MEDIUM: Many shared variables, few locks")
    else:
        print("  ✅ GOOD: Reasonable lock-to-shared-variable ratio")
    
    print(f"\n🏆 OVERALL THREAD SAFETY SCORE: {max(0, 10 - risk_score)}/10")
    
    if risk_score >= 5:
        print("🚨 RECOMMENDATION: Immediate thread safety review required")
    elif risk_score >= 3:
        print("⚠️  RECOMMENDATION: Thread safety audit recommended")
    else:
        print("✅ RECOMMENDATION: Thread safety appears adequate")


if __name__ == "__main__":
    try:
        analysis = analyze_project()
        print_thread_safety_report(analysis)
        
        # Save detailed report
        import json
        with open('thread_safety_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed report saved to: thread_safety_analysis.json")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        exit(1)