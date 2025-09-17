#!/usr/bin/env python3
"""
Quick test script to check for nested expanders in the improved app
"""

import re

def check_nested_expanders(file_path):
    """Check for potential nested expanders in the file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    expander_stack = []
    nested_issues = []
    
    for i, line in enumerate(lines, 1):
        # Count indentation
        indent_level = len(line) - len(line.lstrip())
        
        # Check for expander start
        if 'with st.expander(' in line:
            expander_stack.append((i, indent_level, line.strip()))
        
        # Check if we're inside an expander and find another one
        elif expander_stack:
            # If we find another expander with deeper indentation
            if 'with st.expander(' in line:
                parent_line, parent_indent, parent_text = expander_stack[-1]
                if indent_level > parent_indent:
                    nested_issues.append({
                        'parent_line': parent_line,
                        'parent_text': parent_text,
                        'nested_line': i,
                        'nested_text': line.strip()
                    })
            
            # Remove expanders from stack when we go back to lower indentation
            expander_stack = [(line_no, indent, text) for line_no, indent, text in expander_stack if indent < indent_level]
    
    return nested_issues

def main():
    file_path = "review_app_improved.py"
    
    print("🔍 Checking for nested expanders...")
    nested_issues = check_nested_expanders(file_path)
    
    if nested_issues:
        print(f"❌ Found {len(nested_issues)} potential nested expander issues:")
        for issue in nested_issues:
            print(f"  Line {issue['parent_line']}: {issue['parent_text']}")
            print(f"    └─ Line {issue['nested_line']}: {issue['nested_text']}")
            print()
    else:
        print("✅ No nested expander issues found!")
    
    # Also check for basic syntax by trying to compile
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        compile(content, file_path, 'exec')
        print("✅ File compiles without syntax errors")
    except SyntaxError as e:
        print(f"❌ Syntax error found: {e}")
        print(f"   Line {e.lineno}: {e.text}")

if __name__ == "__main__":
    main()
