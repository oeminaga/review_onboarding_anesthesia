#!/usr/bin/env python3
"""
Quick validation script for Streamlit component requirements
"""

import re
import sys

def check_text_area_heights(file_path):
    """Check if all text areas have valid heights (>= 68px)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all height specifications
        height_matches = re.finditer(r'height=(\d+)', content)
        heights = [int(match.group(1)) for match in height_matches]
        
        # Check for invalid heights
        invalid_heights = [h for h in heights if h < 68]
        
        if invalid_heights:
            print(f"❌ Invalid text area heights found: {invalid_heights}")
            print("   Streamlit requires text areas to have height >= 68px")
            return False
        else:
            print("✅ All text area heights are valid (>= 68px)")
            return True
            
    except Exception as e:
        print(f"❌ Error checking heights: {e}")
        return False

def check_component_issues(file_path):
    """Check for common Streamlit component issues"""
    print("🔍 Checking Streamlit component requirements...")
    
    all_good = True
    
    # Check text area heights
    if not check_text_area_heights(file_path):
        all_good = False
    
    # Could add more checks here in the future
    # - Column width validation
    # - Key uniqueness
    # - etc.
    
    return all_good

def main():
    file_path = "review_app_improved.py"
    
    if check_component_issues(file_path):
        print("✅ All component validations passed!")
        sys.exit(0)
    else:
        print("❌ Some component issues found!")
        sys.exit(1)

if __name__ == "__main__":
    main()
