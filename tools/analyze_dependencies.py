#!/usr/bin/env python3
"""
Dependency Analysis Tool for Screen Translator v2.0
Analyzes import dependencies, circular imports, and missing modules
"""

import ast
import os
import sys
from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque
import importlib.util


class DependencyAnalyzer(ast.NodeVisitor):
    """Analyzes Python dependencies"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports = []
        self.from_imports = []
        self.local_imports = []
        self.external_imports = []
        
    def visit_Import(self, node):
        """Handle regular import statements"""
        for alias in node.names:
            import_info = {
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'type': 'import'
            }
            self.imports.append(import_info)
            
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """Handle from...import statements"""
        module = node.module or ''
        for alias in node.names:
            import_info = {
                'module': module,
                'name': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'level': node.level,
                'type': 'from_import'
            }
            self.from_imports.append(import_info)
            
        self.generic_visit(node)
        
    def categorize_imports(self):
        """Categorize imports as local vs external"""
        for imp in self.imports + self.from_imports:
            module = imp['module']
            if module.startswith('src.') or module.startswith('.'):
                self.local_imports.append(imp)
            else:
                self.external_imports.append(imp)
                
    def get_dependencies(self) -> Dict:
        """Get all dependencies for this file"""
        self.categorize_imports()
        return {
            'file': self.file_path,
            'all_imports': self.imports + self.from_imports,
            'local_imports': self.local_imports,
            'external_imports': self.external_imports,
            'import_count': len(self.imports + self.from_imports),
            'local_count': len(self.local_imports),
            'external_count': len(self.external_imports)
        }


def analyze_file_dependencies(file_path: str) -> Dict:
    """Analyze dependencies for a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        analyzer = DependencyAnalyzer(file_path)
        analyzer.visit(tree)
        
        return analyzer.get_dependencies()
        
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e),
            'all_imports': [],
            'local_imports': [],
            'external_imports': [],
            'import_count': 0,
            'local_count': 0,
            'external_count': 0
        }


def find_circular_imports(dependency_graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Find circular dependencies using DFS"""
    def dfs(node, path, visited, rec_stack):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in dependency_graph.get(node, set()):
            if neighbor not in visited:
                result = dfs(neighbor, path, visited, rec_stack)
                if result:
                    return result
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]
                
        rec_stack.remove(node)
        path.pop()
        return None
    
    cycles = []
    visited = set()
    
    for node in dependency_graph:
        if node not in visited:
            cycle = dfs(node, [], visited, set())
            if cycle:
                cycles.append(cycle)
                
    return cycles


def check_external_dependencies() -> Dict:
    """Check availability of external dependencies"""
    # Common dependencies in the project
    known_deps = [
        'tkinter', 'PIL', 'cv2', 'numpy', 'requests', 'pytesseract',
        'pyttsx3', 'keyboard', 'pystray', 'googletrans', 'pyperclip',
        'psutil', 'defusedxml', 'sqlalchemy', 'aiohttp', 'asyncio',
        'threading', 'json', 'xml', 'csv', 'sqlite3', 'queue',
        'logging', 'pathlib', 'dataclasses', 'typing', 'enum',
        'datetime', 'time', 'os', 'sys', 'io', 're', 'warnings'
    ]
    
    available = []
    missing = []
    
    for dep in known_deps:
        try:
            spec = importlib.util.find_spec(dep)
            if spec is not None:
                available.append(dep)
            else:
                missing.append(dep)
        except (ImportError, ValueError, ModuleNotFoundError):
            missing.append(dep)
            
    return {
        'available': available,
        'missing': missing,
        'total_checked': len(known_deps),
        'availability_rate': len(available) / len(known_deps) * 100
    }


def analyze_project_dependencies() -> Dict:
    """Analyze dependencies for entire project"""
    print("🔍 Analyzing Dependencies in Screen Translator v2.0...")
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"📁 Found {len(python_files)} Python files to analyze")
    
    # Analyze each file
    file_dependencies = []
    dependency_graph = defaultdict(set)
    all_external_imports = set()
    
    for file_path in python_files:
        deps = analyze_file_dependencies(file_path)
        file_dependencies.append(deps)
        
        # Build dependency graph for circular import detection
        for imp in deps['local_imports']:
            module = imp['module']
            if module.startswith('src.'):
                dependency_graph[file_path].add(module)
        
        # Collect all external imports
        for imp in deps['external_imports']:
            all_external_imports.add(imp['module'])
    
    # Find circular imports
    circular_imports = find_circular_imports(dependency_graph)
    
    # Check external dependency availability
    external_deps = check_external_dependencies()
    
    # Calculate statistics
    total_imports = sum(deps['import_count'] for deps in file_dependencies)
    total_local = sum(deps['local_count'] for deps in file_dependencies)
    total_external = sum(deps['external_count'] for deps in file_dependencies)
    
    # Find most imported modules
    import_counts = defaultdict(int)
    for deps in file_dependencies:
        for imp in deps['all_imports']:
            import_counts[imp['module']] += 1
    
    most_imported = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Find files with most dependencies
    files_by_deps = sorted(file_dependencies, key=lambda x: x['import_count'], reverse=True)
    
    return {
        'files_analyzed': len(python_files),
        'file_dependencies': file_dependencies,
        'circular_imports': circular_imports,
        'external_dependencies': external_deps,
        'statistics': {
            'total_imports': total_imports,
            'total_local_imports': total_local,
            'total_external_imports': total_external,
            'unique_external_modules': len(all_external_imports),
            'average_imports_per_file': total_imports / len(python_files) if python_files else 0
        },
        'most_imported_modules': most_imported[:20],
        'files_with_most_dependencies': files_by_deps[:10],
        'dependency_graph': dict(dependency_graph)
    }


def print_dependency_report(analysis: Dict):
    """Print formatted dependency analysis report"""
    print("\n" + "="*60)
    print("📦 DEPENDENCY ANALYSIS REPORT")
    print("="*60)
    
    stats = analysis['statistics']
    
    print(f"\n📊 SUMMARY:")
    print(f"  Files analyzed: {analysis['files_analyzed']}")
    print(f"  Total imports: {stats['total_imports']}")
    print(f"  Local imports: {stats['total_local_imports']}")
    print(f"  External imports: {stats['total_external_imports']}")
    print(f"  Unique external modules: {stats['unique_external_modules']}")
    print(f"  Average imports per file: {stats['average_imports_per_file']:.1f}")
    
    # External dependencies
    ext_deps = analysis['external_dependencies']
    print(f"\n📦 EXTERNAL DEPENDENCIES:")
    print(f"  Availability rate: {ext_deps['availability_rate']:.1f}%")
    print(f"  Available: {len(ext_deps['available'])}")
    print(f"  Missing: {len(ext_deps['missing'])}")
    
    if ext_deps['missing']:
        print(f"\n❌ MISSING DEPENDENCIES:")
        for dep in ext_deps['missing'][:10]:
            print(f"    - {dep}")
        if len(ext_deps['missing']) > 10:
            print(f"    ... and {len(ext_deps['missing']) - 10} more")
    
    # Circular imports
    if analysis['circular_imports']:
        print(f"\n🔄 CIRCULAR IMPORTS DETECTED:")
        for i, cycle in enumerate(analysis['circular_imports'][:5]):
            print(f"  Cycle {i+1}: {' -> '.join(cycle)}")
        if len(analysis['circular_imports']) > 5:
            print(f"  ... and {len(analysis['circular_imports']) - 5} more cycles")
    else:
        print(f"\n✅ NO CIRCULAR IMPORTS DETECTED")
    
    # Most imported modules
    print(f"\n📈 MOST IMPORTED MODULES:")
    for module, count in analysis['most_imported_modules'][:10]:
        module_short = module.replace('src.', '') if module.startswith('src.') else module
        print(f"  {module_short}: {count} imports")
    
    # Files with most dependencies
    print(f"\n📁 FILES WITH MOST DEPENDENCIES:")
    for deps in analysis['files_with_most_dependencies']:
        file_short = deps['file'].replace('src/', '')
        print(f"  {file_short}: {deps['import_count']} imports ({deps['local_count']} local, {deps['external_count']} external)")
    
    # Dependency health assessment
    print(f"\n🎯 DEPENDENCY HEALTH:")
    
    issues = []
    
    if ext_deps['availability_rate'] < 80:
        issues.append("⚠️  Many external dependencies missing")
    elif ext_deps['availability_rate'] < 90:
        issues.append("⚠️  Some external dependencies missing")
    else:
        print("  ✅ Good external dependency availability")
    
    if analysis['circular_imports']:
        issues.append(f"⚠️  {len(analysis['circular_imports'])} circular import cycles detected")
    else:
        print("  ✅ No circular imports")
    
    if stats['average_imports_per_file'] > 20:
        issues.append("⚠️  High coupling - many imports per file")
    elif stats['average_imports_per_file'] > 15:
        issues.append("⚠️  Moderate coupling - consider reducing dependencies")
    else:
        print("  ✅ Reasonable import coupling")
    
    # Show issues
    for issue in issues:
        print(f"  {issue}")
    
    # Overall assessment
    risk_score = 0
    risk_score += len(analysis['circular_imports']) * 2
    risk_score += max(0, 10 - int(ext_deps['availability_rate'] / 10))
    risk_score += max(0, int(stats['average_imports_per_file'] / 5) - 2)
    
    print(f"\n🏆 DEPENDENCY HEALTH SCORE: {max(0, 10 - risk_score)}/10")
    
    if risk_score >= 6:
        print("🚨 RECOMMENDATION: Immediate dependency refactoring required")
    elif risk_score >= 4:
        print("⚠️  RECOMMENDATION: Dependency cleanup recommended")
    else:
        print("✅ RECOMMENDATION: Dependency structure is healthy")


if __name__ == "__main__":
    try:
        analysis = analyze_project_dependencies()
        print_dependency_report(analysis)
        
        # Save detailed report
        import json
        with open('dependency_analysis.json', 'w', encoding='utf-8') as f:
            # Convert sets to lists for JSON serialization
            json_analysis = analysis.copy()
            for key, value in json_analysis['dependency_graph'].items():
                if isinstance(value, set):
                    json_analysis['dependency_graph'][key] = list(value)
            json.dump(json_analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed report saved to: dependency_analysis.json")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        exit(1)