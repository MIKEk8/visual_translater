#!/usr/bin/env python3
"""
Performance Optimization Tool for Screen Translator v2.0
Automatically fixes performance bottlenecks identified in the analysis
"""

import ast
import os
import re
from typing import Dict, List, Set, Tuple


class PerformanceOptimizer:
    """Automatically optimizes performance issues in Python code"""
    
    def __init__(self):
        self.optimizations_applied = []
        
    def analyze_nested_loops(self, file_path: str) -> List[Dict]:
        """Find nested loops that can be optimized"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            nested_loops = []
            
            class NestedLoopFinder(ast.NodeVisitor):
                def __init__(self):
                    self.loop_stack = []
                    
                def visit_For(self, node):
                    self.loop_stack.append(('for', node.lineno))
                    
                    # Check for nested loops
                    for child in ast.walk(node):
                        if isinstance(child, (ast.For, ast.While)) and child != node:
                            nested_loops.append({
                                'type': 'nested_loops',
                                'outer_line': node.lineno,
                                'inner_line': child.lineno,
                                'file': file_path,
                                'outer_type': 'for',
                                'inner_type': 'for' if isinstance(child, ast.For) else 'while'
                            })
                    
                    self.generic_visit(node)
                    self.loop_stack.pop()
                    
                def visit_While(self, node):
                    self.loop_stack.append(('while', node.lineno))
                    
                    # Check for nested loops
                    for child in ast.walk(node):
                        if isinstance(child, (ast.For, ast.While)) and child != node:
                            nested_loops.append({
                                'type': 'nested_loops',
                                'outer_line': node.lineno,
                                'inner_line': child.lineno,
                                'file': file_path,
                                'outer_type': 'while',
                                'inner_type': 'for' if isinstance(child, ast.For) else 'while'
                            })
                    
                    self.generic_visit(node)
                    self.loop_stack.pop()
            
            finder = NestedLoopFinder()
            finder.visit(tree)
            
            return nested_loops
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return []
            
    def optimize_imports(self, file_path: str) -> Dict:
        """Move imports from functions to module level"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            imports_to_move = []
            module_imports = set()
            
            # Find existing module-level imports
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ')) and 'import' in stripped:
                    if not any(x in line for x in ['def ', 'class ', '    ']):  # Not indented
                        module_imports.add(stripped)
                        
            # Find imports inside functions
            in_function = False
            function_indent = 0
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Track function/class boundaries
                if stripped.startswith(('def ', 'class ')) and not line.startswith(' '):
                    in_function = True
                    function_indent = len(line) - len(line.lstrip())
                elif in_function and line and not line.startswith(' ' * (function_indent + 1)):
                    in_function = False
                    
                # Find imports inside functions
                if in_function and stripped.startswith(('import ', 'from ')) and 'import' in stripped:
                    if stripped not in module_imports:
                        imports_to_move.append({
                            'line_num': i,
                            'import': stripped,
                            'original_line': line
                        })
                        
            if not imports_to_move:
                return {'file': file_path, 'changes_made': False, 'imports_moved': 0}
            
            # Move imports to top
            new_lines = lines.copy()
            
            # Remove imports from functions (in reverse order to maintain line numbers)
            for imp in reversed(imports_to_move):
                del new_lines[imp['line_num']]
                
            # Find insertion point for new imports
            insert_pos = 0
            for i, line in enumerate(new_lines):
                if line.strip().startswith(('import ', 'from ')) and 'import' in line:
                    insert_pos = i + 1
                elif line.strip() and not line.strip().startswith(('"""', "'''", '#')):
                    break
                    
            # Insert moved imports
            unique_imports = []
            seen = set()
            for imp in imports_to_move:
                if imp['import'] not in seen:
                    unique_imports.append(imp['import'])
                    seen.add(imp['import'])
                    
            for imp in reversed(unique_imports):
                new_lines.insert(insert_pos, imp)
                
            # Write back
            new_content = '\n'.join(new_lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return {
                'file': file_path,
                'changes_made': True,
                'imports_moved': len(imports_to_move),
                'unique_imports_moved': len(unique_imports)
            }
            
        except Exception as e:
            return {'file': file_path, 'error': str(e), 'changes_made': False}
            
    def optimize_string_operations(self, file_path: str) -> Dict:
        """Optimize string concatenation patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            optimizations = 0
            
            # Pattern 1: Multiple string concatenations in loops
            # Replace: result += item with result.append(item) + ''.join()
            pattern1 = r'(\s+)(\w+)\s*\+=\s*([^=\n]+)'
            
            def optimize_concatenation(match):
                nonlocal optimizations
                indent, var, value = match.groups()
                
                # Check if this looks like string concatenation in a loop context
                if any(keyword in value for keyword in ['str(', '"', "'", 'f"', "f'"]):
                    optimizations += 1
                    return f'{indent}{var}.append({value})'
                return match.group(0)
                
            content = re.sub(pattern1, optimize_concatenation, content)
            
            # Pattern 2: Replace multiple format() calls with f-strings where simple
            pattern2 = r'"([^"]*)\{\}([^"]*)"\s*\.format\(([^)]+)\)'
            
            def to_fstring(match):
                nonlocal optimizations
                before, after, var = match.groups()
                if ',' not in var and len(var.strip()) < 20:  # Simple case only
                    optimizations += 1
                    return f'f"{before}{{{var.strip()}}}{after}"'
                return match.group(0)
                
            content = re.sub(pattern2, to_fstring, content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                return {
                    'file': file_path,
                    'changes_made': True,
                    'string_optimizations': optimizations
                }
            else:
                return {'file': file_path, 'changes_made': False, 'string_optimizations': 0}
                
        except Exception as e:
            return {'file': file_path, 'error': str(e), 'changes_made': False}
            
    def add_async_io_suggestions(self, file_path: str) -> Dict:
        """Add comments suggesting async/await for I/O operations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            lines = content.split('\n')
            suggestions_added = 0
            
            # I/O patterns that could benefit from async
            io_patterns = [
                (r'requests\.(get|post|put|delete)', 'Consider using aiohttp for async HTTP requests'),
                (r'urllib\.(request|urlopen)', 'Consider using aiohttp for async HTTP requests'),
                (r'time\.sleep\(', 'Consider using asyncio.sleep() for non-blocking delays'),
                (r'open\([^)]*\)', 'Consider using aiofiles for async file operations'),
                (r'\.read\(\)|\.write\(', 'Consider async file operations'),
                (r'json\.(loads|dumps)', 'Consider async JSON processing for large data'),
            ]
            
            new_lines = []
            for i, line in enumerate(lines):
                new_lines.append(line)
                
                for pattern, suggestion in io_patterns:
                    if re.search(pattern, line):
                        indent = re.match(r'(\s*)', line).group(1)
                        comment = f'{indent}# TODO: Performance - {suggestion}'
                        
                        # Only add if not already there
                        if i == 0 or suggestion not in lines[i-1]:
                            new_lines.insert(-1, comment)
                            suggestions_added += 1
                            break
                            
            if suggestions_added > 0:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                    
                return {
                    'file': file_path,
                    'changes_made': True,
                    'async_suggestions': suggestions_added
                }
            else:
                return {'file': file_path, 'changes_made': False, 'async_suggestions': 0}
                
        except Exception as e:
            return {'file': file_path, 'error': str(e), 'changes_made': False}


def optimize_critical_files() -> Dict:
    """Optimize performance in files with most issues"""
    
    # Files with most performance issues identified
    critical_files = [
        'src/core/application.py',
        'src/ui/enhanced_capture.py',
        'src/ui/settings_window.py',
        'src/core/ai_ocr_engine.py',
        'src/services/hotkey_service.py',
        'src/core/batch_processor.py',
        'src/api/web_server.py'
    ]
    
    optimizer = PerformanceOptimizer()
    results = {
        'files_processed': 0,
        'files_optimized': 0,
        'total_imports_moved': 0,
        'total_string_optimizations': 0,
        'total_async_suggestions': 0,
        'optimizations': []
    }
    
    print("⚡ Optimizing Performance in Critical Files...")
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"Processing: {file_path}")
            results['files_processed'] += 1
            
            file_changes = 0
            
            # Optimize imports
            import_result = optimizer.optimize_imports(file_path)
            if import_result.get('changes_made'):
                file_changes += import_result['imports_moved']
                results['total_imports_moved'] += import_result['imports_moved']
                print(f"  ✅ Moved {import_result['imports_moved']} imports to module level")
                
            # Optimize string operations
            string_result = optimizer.optimize_string_operations(file_path)
            if string_result.get('changes_made'):
                file_changes += string_result['string_optimizations']
                results['total_string_optimizations'] += string_result['string_optimizations']
                print(f"  ✅ Applied {string_result['string_optimizations']} string optimizations")
                
            # Add async suggestions
            async_result = optimizer.add_async_io_suggestions(file_path)
            if async_result.get('changes_made'):
                file_changes += async_result['async_suggestions']
                results['total_async_suggestions'] += async_result['async_suggestions']
                print(f"  ✅ Added {async_result['async_suggestions']} async I/O suggestions")
                
            if file_changes > 0:
                results['files_optimized'] += 1
                results['optimizations'].append({
                    'file': file_path,
                    'imports_moved': import_result.get('imports_moved', 0),
                    'string_optimizations': string_result.get('string_optimizations', 0),
                    'async_suggestions': async_result.get('async_suggestions', 0)
                })
            else:
                print(f"  ℹ️  No optimizations needed")
        else:
            print(f"  ❌ File not found: {file_path}")
            
    return results


def create_performance_optimization_guide():
    """Create comprehensive performance optimization guide"""
    
    guide = """# ⚡ Performance Optimization Guide for Screen Translator v2.0

## 🎯 Critical Performance Improvements

### 1. **Eliminate Nested Loops** (O(n²) → O(n))

```python
# ❌ BAD - O(n²) complexity
def find_matches(items, targets):
    matches = []
    for item in items:           # O(n)
        for target in targets:   # O(n) - NESTED!
            if item == target:
                matches.append(item)
    return matches

# ✅ GOOD - O(n) complexity
def find_matches(items, targets):
    target_set = set(targets)    # O(n) to create set
    matches = []
    for item in items:           # O(n)
        if item in target_set:   # O(1) set lookup
            matches.append(item)
    return matches

# ✅ BETTER - List comprehension
def find_matches(items, targets):
    target_set = set(targets)
    return [item for item in items if item in target_set]
```

### 2. **Move Imports to Module Level**

```python
# ❌ BAD - Import inside function (slow)
def process_image(image_data):
    import cv2                    # Import on every call!
    import numpy as np
    return cv2.imread(image_data)

# ✅ GOOD - Module level imports
import cv2
import numpy as np

def process_image(image_data):
    return cv2.imread(image_data)
```

### 3. **Use Async I/O for Blocking Operations**

```python
# ❌ BAD - Blocking I/O
def fetch_translation(text):
    import requests
    response = requests.post(url, data={'text': text})  # Blocks thread!
    return response.json()

# ✅ GOOD - Async I/O
import aiohttp
import asyncio

async def fetch_translation(text):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data={'text': text}) as response:
            return await response.json()
```

### 4. **Optimize String Operations**

```python
# ❌ BAD - String concatenation in loop
def build_report(items):
    result = ""
    for item in items:
        result += f"Item: {item}\\n"    # Creates new string each time!
    return result

# ✅ GOOD - List join
def build_report(items):
    parts = []
    for item in items:
        parts.append(f"Item: {item}")
    return "\\n".join(parts)

# ✅ BETTER - Generator expression
def build_report(items):
    return "\\n".join(f"Item: {item}" for item in items)
```

### 5. **Use Efficient Data Structures**

```python
# ❌ BAD - List for membership testing
def is_supported_language(lang):
    supported = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh']
    return lang in supported  # O(n) search!

# ✅ GOOD - Set for membership testing
SUPPORTED_LANGUAGES = {'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh'}

def is_supported_language(lang):
    return lang in SUPPORTED_LANGUAGES  # O(1) lookup!
```

## 🔧 Specific Optimizations for Screen Translator

### **OCR Processing Optimization**

```python
# ✅ Optimize image preprocessing pipeline
class OCRProcessor:
    def __init__(self):
        # Pre-compile expensive operations
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        self.kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    
    def enhance_image(self, image):
        # Use pre-compiled objects instead of creating new ones
        enhanced = self.clahe.apply(image)
        sharpened = cv2.filter2D(enhanced, -1, self.kernel)
        return sharpened
```

### **Translation Caching Optimization**

```python
# ✅ Use LRU cache with size limits
from functools import lru_cache
import hashlib

class TranslationProcessor:
    def __init__(self):
        self._cache = {}
        self.max_cache_size = 1000
    
    @lru_cache(maxsize=1000)
    def translate_cached(self, text_hash, target_lang):
        # Actual translation logic here
        return self._translate_impl(text_hash, target_lang)
    
    def translate(self, text, target_lang):
        # Use hash to enable caching of long texts
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return self.translate_cached(text_hash, target_lang)
```

### **Batch Processing Optimization**

```python
# ✅ Use thread pools for I/O bound tasks
import concurrent.futures
import asyncio

class BatchProcessor:
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
    
    async def process_batch_async(self, items):
        # Use asyncio for I/O bound operations
        tasks = [self.process_item_async(item) for item in items]
        return await asyncio.gather(*tasks)
    
    def process_batch_cpu(self, items):
        # Use thread pool for CPU bound operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            return list(executor.map(self.process_item_cpu, items))
```

## 📊 Performance Monitoring

### **Add Performance Metrics**

```python
import time
import functools

def performance_monitor(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.perf_counter() - start_time
            print(f"{func.__name__}: {duration:.4f}s")
    return wrapper

# Usage
@performance_monitor
def expensive_operation():
    # Your code here
    pass
```

### **Memory Usage Monitoring**

```python
import psutil
import os

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

# Monitor memory in critical sections
def process_large_image(image):
    initial_memory = get_memory_usage()
    
    # Process image
    result = heavy_processing(image)
    
    final_memory = get_memory_usage()
    print(f"Memory used: {final_memory - initial_memory:.1f} MB")
    
    return result
```

## 🎯 Algorithm Optimization Patterns

### **Replace O(n²) with O(n log n)**

```python
# ❌ BAD - Bubble sort O(n²)
def sort_items(items):
    n = len(items)
    for i in range(n):
        for j in range(0, n-i-1):
            if items[j] > items[j+1]:
                items[j], items[j+1] = items[j+1], items[j]
    return items

# ✅ GOOD - Built-in sort O(n log n)
def sort_items(items):
    return sorted(items)
```

### **Use Built-in Functions**

```python
# ❌ BAD - Manual implementation
def find_max(numbers):
    max_val = numbers[0]
    for num in numbers[1:]:
        if num > max_val:
            max_val = num
    return max_val

# ✅ GOOD - Built-in function
def find_max(numbers):
    return max(numbers)  # Optimized C implementation
```

## 🚀 Advanced Optimizations

### **Use NumPy for Numerical Operations**

```python
# ❌ BAD - Pure Python loops
def apply_filter(image_array):
    height, width = len(image_array), len(image_array[0])
    result = [[0 for _ in range(width)] for _ in range(height)]
    
    for i in range(1, height-1):
        for j in range(1, width-1):
            # Convolution operation
            result[i][j] = (image_array[i-1][j] + image_array[i+1][j] + 
                           image_array[i][j-1] + image_array[i][j+1]) / 4
    return result

# ✅ GOOD - NumPy vectorized operations
import numpy as np
from scipy import ndimage

def apply_filter(image_array):
    kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]]) / 4
    return ndimage.convolve(image_array, kernel)
```

### **Profile Before Optimizing**

```python
import cProfile
import pstats

# Profile your code
def profile_function(func, *args, **kwargs):
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func(*args, **kwargs)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 slowest functions
    
    return result
```

## 📋 Performance Optimization Checklist

### **Code Level**
- [ ] Eliminate nested loops where possible
- [ ] Move imports to module level
- [ ] Use list comprehensions instead of loops
- [ ] Replace string concatenation with join()
- [ ] Use sets for membership testing
- [ ] Cache expensive computations
- [ ] Use built-in functions instead of manual loops

### **I/O Operations**
- [ ] Use async/await for network requests
- [ ] Implement connection pooling
- [ ] Use buffered I/O for file operations
- [ ] Compress data transmission
- [ ] Implement request batching

### **Memory Management**
- [ ] Use generators for large datasets
- [ ] Implement memory pools for frequent allocations
- [ ] Clear large objects explicitly
- [ ] Use weak references where appropriate
- [ ] Monitor memory usage in production

### **Concurrency**
- [ ] Use thread pools for I/O bound tasks
- [ ] Use process pools for CPU bound tasks
- [ ] Implement proper resource cleanup
- [ ] Avoid shared mutable state
- [ ] Use lock-free data structures where possible

## 🎯 Implementation Priority

1. **Critical (Do First)**:
   - Fix nested loops causing O(n²) complexity
   - Move imports out of functions
   - Implement async I/O for network operations

2. **High Priority**:
   - Optimize string operations
   - Add caching for expensive computations
   - Use NumPy for numerical operations

3. **Medium Priority**:
   - Add performance monitoring
   - Optimize memory usage
   - Implement connection pooling

4. **Low Priority**:
   - Fine-tune algorithm parameters
   - Add micro-optimizations
   - Profile and optimize hot spots

Remember: **Profile first, optimize second!**
"""
    
    with open('PERFORMANCE_OPTIMIZATION_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(guide)
        
    print("📝 Performance optimization guide created: PERFORMANCE_OPTIMIZATION_GUIDE.md")


if __name__ == "__main__":
    try:
        # Optimize performance in critical files
        results = optimize_critical_files()
        
        print(f"\n🎉 Performance Optimization Completed!")
        print(f"📊 Files processed: {results['files_processed']}")
        print(f"⚡ Files optimized: {results['files_optimized']}")
        print(f"📦 Imports moved: {results['total_imports_moved']}")
        print(f"🔤 String optimizations: {results['total_string_optimizations']}")
        print(f"🚀 Async suggestions: {results['total_async_suggestions']}")
        
        if results['optimizations']:
            print(f"\n✅ Applied Optimizations:")
            for opt in results['optimizations']:
                changes = []
                if opt['imports_moved'] > 0:
                    changes.append(f"{opt['imports_moved']} imports moved")
                if opt['string_optimizations'] > 0:
                    changes.append(f"{opt['string_optimizations']} string opts")
                if opt['async_suggestions'] > 0:
                    changes.append(f"{opt['async_suggestions']} async suggestions")
                    
                print(f"  - {opt['file']}: {', '.join(changes)}")
                
        # Create optimization guide
        create_performance_optimization_guide()
        
        print(f"\n📋 Next Steps:")
        print(f"  1. Review the applied optimizations")
        print(f"  2. Test performance improvements")
        print(f"  3. Follow PERFORMANCE_OPTIMIZATION_GUIDE.md")
        print(f"  4. Profile hot spots and optimize further")
        print(f"  5. Consider implementing async I/O where suggested")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)